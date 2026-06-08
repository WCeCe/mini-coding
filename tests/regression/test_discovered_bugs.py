"""QA_LOG 轮次 0 已知问题 → regression class（L1/L2 可复现，不依赖 Ollama）。"""

import json
from pathlib import Path

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.executor import execute_dag
from mini_coding_agent.modes.graph.nodes.generate import run_generate
from mini_coding_agent.modes.graph.nodes.verify import run_verify
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.modes.graph.verify_rules import collect_tests_snapshot, resolve_test_command
from mini_coding_agent.platform.protocol import parse
from mini_coding_agent.platform.wait_display import set_wait_display_enabled


def _build_agent(tmp_path, outputs):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=FakeModelClient(outputs),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )


def _setup_sum_task(tmp_path: Path, *, buggy: bool = True) -> None:
    loop = "for i in range(1, n):" if buggy else "for i in range(1, n + 1):"
    (tmp_path / "sum_first.py").write_text(
        f"def sum_first(n):\n    s = 0\n    {loop}\n        s += i\n    return s\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_sum.py").write_text(
        "from sum_first import sum_first\n\n"
        "def test_sum_first():\n    assert sum_first(3) == 6\n",
        encoding="utf-8",
    )


def _verify_ctx(tmp_path, path="sum_first.py") -> HarnessContext:
    agent = _build_agent(tmp_path, [])
    dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message="pytest fail",
        test_baseline=collect_tests_snapshot(tmp_path),
    )
    ctx.node_outputs["generate"] = NodeResult(ok=True, message="ok", data={"path": path})
    return ctx


def _fix_bug_ctx(tmp_path, agent, user_message="SyntaxError in calc.py") -> HarnessContext:
    dag = plan("fix_bug", user_message=user_message, workspace_root=tmp_path)
    calc_text = (tmp_path / "calc.py").read_text(encoding="utf-8")
    return HarnessContext(
        agent=agent,
        dag=dag,
        user_message=user_message,
        node_outputs={
            "locate": NodeResult(
                ok=True,
                message="ok",
                data={
                    "files": ["calc.py"],
                    "snippets": [f"# file: calc.py L1-L10\n   1: {line}" for line in calc_text.splitlines()],
                },
            )
        },
    )


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


class TestBug_VerifyPytestNotPycompile:
    """QA_LOG 轮次 0 · off_by_one verify 假阳（EV-1）：有 tests/ 须 pytest 不能仅 py_compile。"""

    def test_resolve_test_command_when_tests_dir_exists(self, tmp_path):
        (tmp_path / "tests").mkdir()
        assert resolve_test_command(tmp_path) == "python -m pytest -q"

    def test_wrong_fix_py_compile_ok_but_pytest_fails(self, tmp_path):
        _setup_sum_task(tmp_path, buggy=False)
        (tmp_path / "sum_first.py").write_text(
            (tmp_path / "sum_first.py").read_text(encoding="utf-8").replace(
                "range(1, n + 1)", "range(1, n + 2)"
            ),
            encoding="utf-8",
        )
        result = run_verify(_verify_ctx(tmp_path))
        assert result.ok is False
        assert result.data.get("method") == "shell"
        assert result.data.get("command") == "python -m pytest -q"

    def test_harness_e2e_wrong_fix_verify_fails(self, tmp_path):
        _setup_sum_task(tmp_path)
        agent = _build_agent(
            tmp_path,
            [
                json.dumps({"intent_id": "fix_bug", "confidence": "high"}),
                (
                    '<tool>{"name":"patch_file","args":{"path":"sum_first.py","new_text":'
                    '"def sum_first(n):\\n    s = 0\\n    for i in range(1, n+2):\\n        s += i\\n    return s\\n"}}</tool>'
                ),
            ],
        )
        dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
        result = execute_dag(agent, dag, "pytest fail")
        assert result.ok is False
        verify = agent.session.get("last_verify")
        assert verify is not None
        assert verify["ok"] is False


class TestBug_PatchOldTextNormalize:
    """QA_LOG 轮次 0 · syntaxerror_paren generate_patch_match（GL-5）：系统注入 old_text。"""

    def test_generate_fix_bug_guided_injects_old_text(self, tmp_path):
        calc = "def add(a, b):\n    return (a + b\n"
        fixed = "def add(a, b):\n    return (a + b)\n"
        (tmp_path / "calc.py").write_text(calc, encoding="utf-8")
        agent = _build_agent(
            tmp_path,
            [
                '<tool>{"name":"patch_file","args":{"path":"calc.py",'
                f'"new_text":{json.dumps(fixed)}}}</tool>',
            ],
        )
        result = run_generate(_fix_bug_ctx(tmp_path, agent))
        assert result.ok
        assert result.data["args"]["old_text"] == calc
        assert (tmp_path / "calc.py").read_text(encoding="utf-8") == fixed


class TestBug_ProtocolNestedQuotes:
    """QA_LOG 轮次 0 · nameerror_greet generate_protocol（GL-5）：嵌套引号/尾 `}` 容错。"""

    def test_protocol_parse_patch_file_with_trailing_brace(self):
        raw = (
            '<tool>{"name":"patch_file","args":{"path":"greet.py",'
            '"old_text":"return msg","new_text":"return f\'Hello, {name}!\'"}}}</tool>'
        )
        kind, payload = parse(raw)
        assert kind == "tool"
        assert payload["name"] == "patch_file"
        assert payload["args"]["new_text"] == "return f'Hello, {name}!'"

    def test_protocol_parse_patch_file_fstring_new_text(self):
        raw = (
            '<tool>{"name":"patch_file","args":{"path":"greet.py",'
            '"old_text":"return msg","new_text":"return f\'Hello, {name}!\'"}}</tool>'
        )
        kind, payload = parse(raw)
        assert kind == "tool"
        assert payload["args"]["new_text"] == "return f'Hello, {name}!'"
