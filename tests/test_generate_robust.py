"""EV-3：Generate / protocol 针对 GL-5 live 失败模式的回归。"""

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.nodes.generate import run_generate
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
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


def _fix_bug_ctx(tmp_path, agent, user_message="SyntaxError in calc.py") -> HarnessContext:
    dag = plan("fix_bug", user_message=user_message, workspace_root=tmp_path)
    return HarnessContext(
        agent=agent,
        dag=dag,
        user_message=user_message,
        node_outputs={
            "locate": NodeResult(
                ok=True,
                message="ok",
                data={"snippets": [(tmp_path / "calc.py").read_text(encoding="utf-8")]},
            )
        },
    )


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_protocol_parse_patch_file_with_trailing_brace():
    """nameerror_greet 类：模型 JSON 尾部多一个 `}`。"""
    raw = (
        '<tool>{"name":"patch_file","args":{"path":"greet.py",'
        '"old_text":"return msg","new_text":"return f\'Hello, {name}!\'"}}}</tool>'
    )
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["name"] == "patch_file"
    assert payload["args"]["new_text"] == "return f'Hello, {name}!'"


def test_protocol_parse_patch_file_fstring_new_text():
    """nameerror_greet 类：new_text 含 f-string 单引号与花括号。"""
    raw = (
        '<tool>{"name":"patch_file","args":{"path":"greet.py",'
        '"old_text":"return msg","new_text":"return f\'Hello, {name}!\'"}}</tool>'
    )
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["args"]["old_text"] == "return msg"
    assert payload["args"]["new_text"] == "return f'Hello, {name}!'"


def test_generate_fix_bug_aligns_patch_old_text_without_indent(tmp_path):
    """syntaxerror_paren 类：old_text 缺缩进时对齐为文件内唯一子串。"""
    calc = "def add(a, b):\n    return (a + b\n"
    (tmp_path / "calc.py").write_text(calc, encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            '<tool>{"name":"patch_file","args":{"path":"calc.py",'
            '"old_text":"return (a + b","new_text":"return (a + b)"}}</tool>',
        ],
    )
    ctx = _fix_bug_ctx(tmp_path, agent)
    result = run_generate(ctx)

    assert result.ok
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == "def add(a, b):\n    return (a + b)\n"


def test_generate_fix_bug_does_not_force_ambiguous_old_text(tmp_path):
    """容错不得把任意 old_text 强行匹配到多处出现。"""
    (tmp_path / "calc.py").write_text("x = 1\nx = 1\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            '<tool>{"name":"patch_file","args":{"path":"calc.py",'
            '"old_text":"x = 1","new_text":"x = 2"}}</tool>',
        ],
    )
    ctx = _fix_bug_ctx(tmp_path, agent, user_message="fix calc.py")
    result = run_generate(ctx)

    assert not result.ok
    assert "old_text" in result.message
