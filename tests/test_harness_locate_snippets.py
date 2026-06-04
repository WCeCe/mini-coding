"""GL-2：Locate 须产出带行号源码 snippet（RIG / search / files_hint 回退）。"""

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.nodes.locate import run_locate
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.snippet import has_source_lines
from mini_coding_agent.modes.graph.types import HarnessContext
from mini_coding_agent.index import build_rig, default_db_path
from mini_coding_agent.platform.wait_display import set_wait_display_enabled


def _write_mini_repo(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "util.py").write_text(
        "def helper():\n    return 1\n",
        encoding="utf-8",
    )
    (pkg / "service.py").write_text(
        "from pkg.util import helper\n\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")


def _agent(tmp_path):
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )


def _locate_ctx(tmp_path, *, user_message: str, symbols_hint: list[str] | None = None):
    agent = _agent(tmp_path)
    dag = plan("fix_bug", user_message=user_message, workspace_root=tmp_path)
    if symbols_hint is not None:
        dag.slots.symbols_hint = symbols_hint
    return HarnessContext(agent=agent, dag=dag, user_message=user_message)


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_locate_without_rig_symbol_hint_has_source_snippets(tmp_path):
    """无 rig.db、仅 symbols_hint：search + read_file 产出源码行。"""
    _write_mini_repo(tmp_path)
    ctx = _locate_ctx(tmp_path, user_message="find helper", symbols_hint=["helper"])
    result = run_locate(ctx)

    assert result.ok
    assert result.data["used_rig"] is False
    assert any(has_source_lines(s) for s in result.data["snippets"])
    joined = "\n".join(result.data["snippets"])
    assert "helper" in joined
    assert "# file: pkg/util.py" in joined
    assert any(line.strip().startswith(("1:", "2:")) or ": def helper" in line for line in joined.splitlines())


def test_locate_with_rig_symbol_hit_has_code_not_only_metadata(tmp_path):
    """有 rig.db、symbol 命中：snippet 含命中行附近代码，非仅 # rig 元数据。"""
    _write_mini_repo(tmp_path)
    build_rig(tmp_path)
    assert default_db_path(tmp_path).is_file()

    ctx = _locate_ctx(
        tmp_path,
        user_message='File "pkg/util.py"\nNameError: name helper',
        symbols_hint=["helper"],
    )
    result = run_locate(ctx)

    assert result.ok
    assert result.data["used_rig"] is True
    assert any(has_source_lines(s) for s in result.data["snippets"])
    joined = "\n".join(result.data["snippets"])
    assert "def helper" in joined
    assert "# file: pkg/util.py" in joined


def test_locate_files_hint_traceback_still_reads_source(tmp_path):
    """traceback files_hint：仍产出 calc.py 源码（E2E 场景不退化）。"""
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    traceback = (
        'Traceback (most recent call last):\n  File "calc.py", line 2, in add\n'
        "    return a + c\nNameError: name 'c' is not defined"
    )
    ctx = _locate_ctx(tmp_path, user_message=traceback)
    result = run_locate(ctx)

    assert result.ok
    assert "calc.py" in result.data["files"]
    assert any(has_source_lines(s) for s in result.data["snippets"])
    assert "return a + c" in "\n".join(result.data["snippets"])
