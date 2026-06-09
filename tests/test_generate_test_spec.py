"""Phase 8.2：generate 从 locate 测试 snippet 注入 assert 规格。"""

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.nodes.generate import _build_generate_prompt, _syntax_repair_hint
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult


def _ctx_with_locate_snippets(tmp_path, snippets: list[str]) -> HarnessContext:
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
        user_message="pytest 失败",
        workspace_root=tmp_path,
    )
    ctx = HarnessContext(agent=agent, dag=dag, user_message="pytest 失败")
    ctx.node_outputs["locate"] = NodeResult(
        ok=True,
        message="ok",
        data={"snippets": snippets, "files": ["greet.py"]},
    )
    return ctx


def test_build_generate_prompt_includes_test_assertions(tmp_path):
    snippet = (
        "# file: tests/test_greet.py L1\n"
        "1: from greet import greet\n"
        "2: \n"
        "3: def test_greet():\n"
        "4:     assert greet(\"Ada\") == \"Ada\"\n"
    )
    ctx = _ctx_with_locate_snippets(tmp_path, [snippet])
    prompt = _build_generate_prompt(ctx)
    assert "测试规格" in prompt
    assert 'assert greet("Ada") == "Ada"' in prompt
    assert "勿擅自改语义" in prompt


def test_syntax_repair_hint_for_syntax_error_goal(tmp_path):
    ctx = _ctx_with_locate_snippets(tmp_path, [])
    ctx.dag.slots.goal = "SyntaxError: '(' was never closed"
    hint = _syntax_repair_hint(ctx)
    assert "括号" in hint
    assert "可编译" in hint


def test_non_fix_bug_template_loads_from_templates_dir(tmp_path):
    from mini_coding_agent.modes.graph.planner import load_template, TEMPLATES_DIR

    path = TEMPLATES_DIR / "explain.json"
    assert path.is_file()
    data = load_template("explain")
    assert data["intent_id"] == "explain"
    assert data["nodes"]
