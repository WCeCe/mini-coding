import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.nodes.locate import run_locate
from mini_coding_agent.modes.graph.snippet import has_source_lines
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import HarnessContext
from mini_coding_agent.index import RigQuery, build_rig, default_db_path, ensure_rig, rig_db_exists
from mini_coding_agent.modes.graph.pipeline import run_pipeline
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

MINI_REPO = """
# pkg/util.py
def helper():
    return 1

# pkg/service.py
from pkg.util import helper

def run():
    return helper()
"""


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


def test_rig_build_mini_repo(tmp_path):
    _write_mini_repo(tmp_path)
    stats = build_rig(tmp_path)
    assert stats["files"] >= 2
    assert stats["symbols"] >= 2
    assert stats["imports"] >= 1
    assert rig_db_exists(tmp_path)
    assert default_db_path(tmp_path).is_file()


def test_rig_query_by_symbol(tmp_path):
    _write_mini_repo(tmp_path)
    build_rig(tmp_path)
    query = RigQuery(default_db_path(tmp_path))
    hits = query.by_symbol("helper")
    assert hits
    assert any(h.file_path.endswith("util.py") for h in hits)
    assert any(h.kind == "function" for h in hits)


def test_rig_query_by_file(tmp_path):
    _write_mini_repo(tmp_path)
    build_rig(tmp_path)
    query = RigQuery(default_db_path(tmp_path))
    hits = query.by_file("pkg/service.py")
    names = {h.name for h in hits}
    assert "run" in names


def test_rig_one_hop_neighbors(tmp_path):
    _write_mini_repo(tmp_path)
    build_rig(tmp_path)
    query = RigQuery(default_db_path(tmp_path))
    neighbors = query.one_hop_neighbors("pkg/service.py")
    assert isinstance(neighbors, list)


def test_locate_uses_rig_when_db_exists(tmp_path):
    _write_mini_repo(tmp_path)
    build_rig(tmp_path)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    agent = MiniAgent(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )
    dag = plan(
        "fix_bug",
        user_message='File "pkg/util.py"\nNameError: name helper',
        workspace_root=tmp_path,
    )
    dag.slots.symbols_hint = ["helper"]
    ctx = HarnessContext(agent=agent, dag=dag, user_message="fix helper")
    result = run_locate(ctx)
    assert result.data["used_rig"] is True
    assert any("pkg/util.py" in f for f in result.data["files"])
    assert any(has_source_lines(s) for s in result.data["snippets"])
    assert any("# rig:" in s for s in result.data["snippets"])


def test_locate_fallback_without_rig_db(tmp_path):
    _write_mini_repo(tmp_path)
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    agent = MiniAgent(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )
    dag = plan("fix_bug", user_message="find helper", workspace_root=tmp_path)
    dag.slots.symbols_hint = ["helper"]
    ctx = HarnessContext(agent=agent, dag=dag, user_message="find helper")

    search_calls = []
    original = agent.run_tool

    def track_search(name, args):
        search_calls.append(name)
        return original(name, args)

    agent.run_tool = track_search
    result = run_locate(ctx)
    assert result.data["used_rig"] is False
    assert "search" in search_calls


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_cli_rig_build(tmp_path, capsys):
    _write_mini_repo(tmp_path)
    from mini_coding_agent.cli import rig_main

    code = rig_main(["build", "--cwd", str(tmp_path)])
    assert code == 0
    captured = capsys.readouterr()
    assert "RIG 构建完成" in captured.err
    assert rig_db_exists(tmp_path)


def test_ensure_rig_builds_when_missing(tmp_path):
    _write_mini_repo(tmp_path)
    assert not rig_db_exists(tmp_path)
    stats = ensure_rig(tmp_path)
    assert stats["built"] is True
    assert rig_db_exists(tmp_path)
    again = ensure_rig(tmp_path)
    assert again["built"] is False


def test_run_pipeline_ensures_rig(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    agent = MiniAgent(
        model_client=FakeModelClient(
            [
                '<tool>{"name":"patch_file","args":{"path":"calc.py",'
                '"new_text":"def add(a, b):\\n    return a + b\\n"}}</tool>',
            ]
        ),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )
    assert not rig_db_exists(tmp_path)
    result = run_pipeline(agent, "fix_bug", 'File "calc.py", line 2')
    assert rig_db_exists(tmp_path)
    assert result.ok
