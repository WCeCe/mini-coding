"""L1 slots + locate 诊断：SL-01–SL-24 子集与 L-01–L-07；D1/D2/D3 量化门槛。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.index import build_rig
from mini_coding_agent.modes.graph.nodes.locate import run_locate
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.slots import (
    detect_test_command,
    extract_files_hint,
    extract_symbols_hint,
    fill_slots,
)
from mini_coding_agent.modes.graph.snippet import has_source_lines
from mini_coding_agent.modes.graph.types import DEFAULT_OPS_ALLOWLIST, HarnessContext
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

_SNIPPET_FILE_HEADER = re.compile(r"# file: .+\.py L\d+-L\d+")

# ---------------------------------------------------------------------------
# D1：files_hint（SL-01–SL-10）
# ---------------------------------------------------------------------------

D1_CASES: list[dict] = [
    {
        "id": "SL-01",
        "message": 'Traceback (most recent call last):\n  File "calc.py", line 2, in add\n    return a + c\nNameError: name \'c\' is not defined',
        "workspace_files": {"calc.py": "def add(a, b):\n    return a + c\n"},
        "expected": ["calc.py"],
    },
    {
        "id": "SL-02",
        "message": "请修复 calc.py 中的错误",
        "workspace_files": {"calc.py": "x = 1\n"},
        "expected": ["calc.py"],
    },
    {
        "id": "SL-03",
        "message": 'File "src/utils/helper.py", line 10',
        "workspace_files": {},
        "expected": ["src/utils/helper.py"],
    },
    {
        "id": "SL-04",
        "message": "修复 greet.py 和 farewell.py",
        "workspace_files": {},
        "expected_contains": ["greet.py", "farewell.py"],
        "order_preserve": True,
    },
    {
        "id": "SL-05",
        "message": 'File "foo\\bar.py", line 1',
        "workspace_files": {},
        "expected": ["foo/bar.py"],
    },
    {
        "id": "SL-06",
        "message": None,
        "abs_path_in_workspace": "calc.py",
        "workspace_files": {"calc.py": "x = 1\n"},
        "expected": ["calc.py"],
    },
    {
        "id": "SL-07",
        "message": None,
        "abs_path_outside": True,
        "workspace_files": {},
        "expected_outside": True,
    },
    {
        "id": "SL-08",
        "message": "The addition function returns wrong results; please fix the logic.",
        "workspace_files": {},
        "expected": [],
    },
    {
        "id": "SL-09",
        "message": "请查看 config.json 与 README.md",
        "workspace_files": {},
        "expected_contains": ["config.json", "README.md"],
    },
    {
        "id": "SL-10",
        "message": "修复 calc.py 以及 calc.py 里的 bug",
        "workspace_files": {},
        "expected": ["calc.py"],
    },
]

# ---------------------------------------------------------------------------
# D2：symbols_hint（SL-11–SL-17）
# ---------------------------------------------------------------------------

D2_CASES: list[dict] = [
    {
        "id": "SL-11",
        "message": "NameError: name 'foo' is not defined",
        "expected_contains": ["foo"],
    },
    {
        "id": "SL-12",
        "message": "AttributeError: 'NoneType' object has no attribute 'bar'",
        "expected_contains": ["bar"],
    },
    {
        "id": "SL-13",
        "message": "ImportError: cannot import name 'baz'",
        "expected_contains": ["baz"],
    },
    {
        "id": "SL-14",
        "message": "ModuleNotFoundError: No module named 'qux'",
        "expected_contains": ["qux"],
    },
    {
        "id": "SL-15",
        "message": 'File "calc.py", line 2, in add\n    return a - b\nadd(2, 3) 得到 -1',
        "expected_contains": ["add"],
    },
    {
        "id": "SL-16",
        "message": "解释 calc.py 做什么",
        "expected_empty_or_no_misleading": True,
    },
    {
        "id": "SL-17",
        "message": 'Traceback (most recent call last):\n  File "calc.py", line 2, in add\n    return a + c',
        "expected_contains": ["add"],
    },
]

# ---------------------------------------------------------------------------
# test_command + fill_slots（SL-18–SL-24）
# ---------------------------------------------------------------------------

SLOTS_EXTRA_CASES: list[dict] = [
    {"id": "SL-18", "kind": "test_command", "setup": "tests_dir", "expected": "python -m pytest -q"},
    {"id": "SL-19", "kind": "test_command", "setup": "pytest_ini", "expected": "python -m pytest -q"},
    {"id": "SL-20", "kind": "test_command", "setup": "pyproject_pytest", "expected": "python -m pytest -q"},
    {"id": "SL-21", "kind": "test_command", "setup": "none", "expected": None},
    {"id": "SL-22", "kind": "fill_slots", "intent_id": "fix_bug", "expect_keys": {"goal", "files_hint", "symbols_hint"}},
    {"id": "SL-23", "kind": "fill_slots", "intent_id": "project_ops", "expect_keys": {"goal", "ops_allowlist"}},
    {"id": "SL-24", "kind": "fill_slots", "intent_id": "fix_bug", "skill_name": "demo-skill", "expect_skill": "demo-skill"},
]

# ---------------------------------------------------------------------------
# D3：locate（L-01–L-07）
# ---------------------------------------------------------------------------

D3_CASES: list[dict] = [
    {
        "id": "L-01",
        "files": {"calc.py": "def add(a, b):\n    return a + c\n"},
        "message": 'Traceback (most recent call last):\n  File "calc.py", line 2, in add\n    return a + c\nNameError: name \'c\' is not defined',
        "d3_required": True,
        "expect_file_in_result": "calc.py",
    },
    {
        "id": "L-02",
        "files": {"calc.py": "def add(a, b):\n    return a + b\n"},
        "message": 'File "calc.py"\nNameError: name add',
        "symbols_hint": ["add"],
        "build_rig": True,
        "expect_used_rig": True,
        "expect_snippets_nonempty": True,
    },
    {
        "id": "L-03",
        "files": {"helper.py": "def mul(a, b):\n    return a * c\n"},
        "message": "NameError: name 'mul' is not defined",
        "symbols_hint": ["mul"],
        "d3_required": True,
        "expect_snippets_nonempty": True,
    },
    {
        "id": "L-04",
        "files": {},
        "message": 'File "missing.py", line 1',
        "expect_no_crash": True,
    },
    {
        "id": "L-05",
        "files": {},
        "message": "fix something",
        "expect_ok": True,
    },
    {
        "id": "L-06",
        "files": {
            "a.py": "def fa():\n    pass\n",
            "b.py": "def fb():\n    pass\n",
        },
        "message": "修复 a.py 和 b.py",
        "expect_multiple_files": True,
    },
    {
        "id": "L-07",
        "files": {"calc.py": "def add(a, b):\n    return a + c\n"},
        "message": 'File "calc.py", line 2, in add',
        "d3_required": True,
        "expect_source_has_def": True,
    },
]


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def _write_workspace(root: Path, files: dict[str, str]) -> None:
    (root / "README.md").write_text("diagnostic\n", encoding="utf-8")
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _locate_agent(root: Path) -> MiniAgent:
    workspace = WorkspaceContext.build(root)
    store = SessionStore(root / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )


def _run_d1_case(case: dict, tmp_path: Path) -> bool:
    _write_workspace(tmp_path, case.get("workspace_files") or {})
    root = tmp_path.resolve()

    if case.get("abs_path_in_workspace"):
        rel = case["abs_path_in_workspace"]
        message = f'File "{root / rel}", line 1'
    elif case.get("abs_path_outside"):
        outside = (tmp_path.parent / "outside_diagnostic_zone" / "other.py").resolve()
        message = f'File "{outside}", line 1'
    else:
        message = case["message"]

    result = extract_files_hint(message, root)

    if "expected" in case:
        expected = case["expected"]
        if case["id"] == "SL-06":
            return bool(result) and result[0] == "calc.py"
        return result == expected
    if contains := case.get("expected_contains"):
        if not all(item in result for item in contains):
            return False
        if case.get("order_preserve"):
            indices = [result.index(item) for item in contains]
            return indices == sorted(indices)
        return True
    if case.get("expected_outside"):
        normalized = [p.replace("\\", "/") for p in result]
        return any("outside_diagnostic_zone/other.py" in p for p in normalized)
    return False


def _run_d2_case(case: dict) -> bool:
    result = extract_symbols_hint(case["message"])
    if case.get("expected_empty_or_no_misleading"):
        misleading = {"calc", "py", "什么", "解释"}
        return not result or not any(s in misleading for s in result)
    contains = case.get("expected_contains") or []
    return all(item in result for item in contains)


def _snippet_passes_d3(snippets: list[str]) -> bool:
    for snippet in snippets:
        if not has_source_lines(snippet):
            continue
        if not _SNIPPET_FILE_HEADER.search(snippet):
            continue
        if re.search(r"\bdef\b|return ", snippet):
            return True
    return False


def _run_d3_case(case: dict, tmp_path: Path) -> bool:
    _write_workspace(tmp_path, case.get("files") or {})
    if case.get("build_rig"):
        build_rig(tmp_path)

    agent = _locate_agent(tmp_path)
    dag = plan("fix_bug", user_message=case["message"], workspace_root=tmp_path)
    if symbols := case.get("symbols_hint"):
        dag.slots.symbols_hint = symbols

    result = run_locate(HarnessContext(agent=agent, dag=dag, user_message=case["message"]))
    snippets = result.data.get("snippets") or []

    if case.get("expect_no_crash"):
        return result.ok is True
    if expected_ok := case.get("expect_ok"):
        return result.ok == expected_ok
    if case.get("expect_used_rig"):
        if result.data.get("used_rig") is not True:
            return False
    if case.get("expect_snippets_nonempty"):
        if not any(has_source_lines(s) for s in snippets):
            return False
    if expect_file := case.get("expect_file_in_result"):
        if expect_file not in result.data.get("files", []):
            return False
    if case.get("expect_multiple_files"):
        files = result.data.get("files") or []
        if len(files) < 2:
            return False
    if case.get("expect_source_has_def"):
        joined = "\n".join(snippets)
        if "def " not in joined:
            return False
    if case.get("d3_required"):
        return _snippet_passes_d3(snippets)
    return True


def _run_slots_extra(case: dict, tmp_path: Path) -> bool:
    if case["kind"] == "test_command":
        setup = case["setup"]
        if setup == "tests_dir":
            (tmp_path / "tests").mkdir()
        elif setup == "pytest_ini":
            (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        elif setup == "pyproject_pytest":
            (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
        return detect_test_command(tmp_path) == case["expected"]

    slots = fill_slots(
        "用户任务消息",
        intent_id=case["intent_id"],
        skill_name=case.get("skill_name"),
        workspace_root=tmp_path,
    )
    if expect_keys := case.get("expect_keys"):
        if not expect_keys.issubset(slots.keys()):
            return False
    if case["intent_id"] == "project_ops":
        if slots.get("ops_allowlist") != list(DEFAULT_OPS_ALLOWLIST):
            return False
    if expect_skill := case.get("expect_skill"):
        return slots.get("skill_name") == expect_skill
    if case["id"] == "SL-22" and (tmp_path / "tests").is_dir():
        return "test_command" in slots
    return True


# ---------------------------------------------------------------------------
# 逐条 parametrized（失败时可见 case id）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", D1_CASES, ids=[c["id"] for c in D1_CASES])
def test_d1_files_hint_case(case, tmp_path):
    assert _run_d1_case(case, tmp_path), case["id"]


@pytest.mark.parametrize("case", D2_CASES, ids=[c["id"] for c in D2_CASES])
def test_d2_symbols_hint_case(case):
    assert _run_d2_case(case), case["id"]


@pytest.mark.parametrize("case", SLOTS_EXTRA_CASES, ids=[c["id"] for c in SLOTS_EXTRA_CASES])
def test_slots_extra_case(case, tmp_path):
    if case["id"] == "SL-22":
        (tmp_path / "tests").mkdir()
    assert _run_slots_extra(case, tmp_path), case["id"]


@pytest.mark.parametrize("case", D3_CASES, ids=[c["id"] for c in D3_CASES])
def test_locate_case(case, tmp_path):
    assert _run_d3_case(case, tmp_path), case["id"]


# ---------------------------------------------------------------------------
# 量化门槛汇总（session 级 D1/D2/D3）
# ---------------------------------------------------------------------------


def test_d1_threshold():
    """D1：SL-01–SL-10 pass rate ≥ 90%。"""
    import tempfile

    passed = 0
    for case in D1_CASES:
        with tempfile.TemporaryDirectory() as td:
            if _run_d1_case(case, Path(td)):
                passed += 1
    rate = passed / len(D1_CASES)
    assert rate >= 0.90, f"D1={rate:.0%} ({passed}/{len(D1_CASES)}), 门槛 90%"


def test_d2_threshold():
    """D2：SL-11–SL-17 pass rate ≥ 85%。"""
    passed = sum(1 for case in D2_CASES if _run_d2_case(case))
    rate = passed / len(D2_CASES)
    assert rate >= 0.85, f"D2={rate:.0%} ({passed}/{len(D2_CASES)}), 门槛 85%"


def test_d3_threshold():
    """D3：L-01/L-03/L-07 有 files_hint 且文件存在时 100%。"""
    import tempfile

    d3_ids = ("L-01", "L-03", "L-07")
    subset = [c for c in D3_CASES if c["id"] in d3_ids]
    passed = 0
    for case in subset:
        with tempfile.TemporaryDirectory() as td:
            if _run_d3_case(case, Path(td)):
                passed += 1
    rate = passed / len(subset)
    assert rate == 1.0, f"D3={rate:.0%} ({passed}/{len(subset)}), 门槛 100%"


def test_diagnostic_sample_count():
    """SL 子集 ≥ 20 样本。"""
    total = len(D1_CASES) + len(D2_CASES) + len(SLOTS_EXTRA_CASES)
    assert total >= 20, f"slots 样本 {total} < 20"
