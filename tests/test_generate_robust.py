"""EV-3：Generate / protocol 针对 GL-5 live 失败模式的回归。"""

import json

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


def test_generate_fix_bug_guided_injects_old_text(tmp_path):
    """Phase 7.2：系统注入 old_text，模型只产 new_text。"""
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
    ctx = _fix_bug_ctx(tmp_path, agent)
    result = run_generate(ctx)

    assert result.ok
    assert result.data["args"]["old_text"] == calc
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == fixed


def test_generate_fix_bug_guided_requires_new_text(tmp_path):
    """引导模式缺少 new_text 时失败。"""
    (tmp_path / "calc.py").write_text("x = 1\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        ['<tool>{"name":"patch_file","args":{"path":"calc.py"}}</tool>'],
    )
    ctx = _fix_bug_ctx(tmp_path, agent, user_message="fix calc.py")
    result = run_generate(ctx)

    assert not result.ok
    assert "new_text" in result.message


def test_protocol_parse_patch_file_new_text_only():
    raw = '<tool>{"name":"patch_file","args":{"path":"foo.py","new_text":"ok"}}</tool>'
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["args"] == {"path": "foo.py", "new_text": "ok"}


def test_protocol_parse_unclosed_new_text_string_syntaxerror_paren():
    """live syntaxerror_paren：new_text 字符串缺少闭合引号。"""
    raw = (
        '<tool>{"name":"patch_file","args":{"path":"calc.py",'
        '"new_text":"def add(a, b):\\n    return (a + b)}}</tool>'
    )
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["args"]["path"] == "calc.py"
    assert payload["args"]["new_text"] == "def add(a, b):\n    return (a + b)"


def test_protocol_parse_unclosed_new_text_fstring_nameerror_greet():
    """live nameerror_greet：new_text 含 f-string 且缺少闭合引号。"""
    raw = (
        '<tool>{"name":"patch_file","args":{"path":"greet.py",'
        '"new_text":"def greet(name):\\n    return f\'Hello, {name}!\'}}</tool>'
    )
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["args"]["new_text"] == "def greet(name):\n    return f'Hello, {name}!'"


def test_protocol_parse_json_fence_wrapping_tool():
    """GN-09：整段响应包在 ```json 围栏内。"""
    inner = '<tool>{"name":"patch_file","args":{"path":"a.py","new_text":"x"}}</tool>'
    raw = f"```json\n{inner}\n```"
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["name"] == "patch_file"


def test_protocol_parse_bare_json_inside_fence():
    raw = '```json\n{"name":"patch_file","args":{"path":"a.py","new_text":"y"}}\n```'
    kind, payload = parse(raw)
    assert kind == "tool"
    assert payload["args"]["new_text"] == "y"


def test_generate_fix_bug_guided_accepts_codeblock_without_tool(tmp_path):
    """引导模式下容忍模型只返回 ``` 代码块（无 <tool>）。"""
    buggy = "def sum_first(n):\n    s = 0\n    for i in range(1, n):\n        s += i\n    return s\n"
    fixed = "def sum_first(n):\n    s = 0\n    for i in range(1, n + 1):\n        s += i\n    return s\n"
    (tmp_path / "sum_first.py").write_text(buggy, encoding="utf-8")
    agent = _build_agent(tmp_path, [f"```\n{fixed}```"])
    dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message="pytest fail",
        node_outputs={
            "locate": NodeResult(
                ok=True,
                message="ok",
                data={"files": ["sum_first.py"], "snippets": []},
            )
        },
    )
    result = run_generate(ctx)
    assert result.ok
    assert (tmp_path / "sum_first.py").read_text(encoding="utf-8").strip() == fixed.strip()


def test_generate_fix_bug_off_by_one_sum_guided(tmp_path):
    """off_by_one_sum：系统注入整文件 old_text，模型只改 range 边界。"""
    buggy = (
        "def sum_first(n):\n"
        "    s = 0\n"
        "    for i in range(1, n):\n"
        "        s += i\n"
        "    return s\n"
    )
    fixed = (
        "def sum_first(n):\n"
        "    s = 0\n"
        "    for i in range(1, n + 1):\n"
        "        s += i\n"
        "    return s\n"
    )
    (tmp_path / "sum_first.py").write_text(buggy, encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            '<tool>{"name":"patch_file","args":{"path":"sum_first.py",'
            f'"new_text":{json.dumps(fixed)}}}</tool>',
        ],
    )
    dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message="pytest fail",
        node_outputs={
            "locate": NodeResult(
                ok=True,
                message="ok",
                data={
                    "files": ["tests/test_sum.py", "sum_first.py"],
                    "snippets": [
                        "# file: sum_first.py L1-L10\n"
                        "   1: def sum_first(n):\n"
                        "   2:     s = 0\n"
                        "   3:     for i in range(1, n):\n"
                        "   4:         s += i\n"
                        "   5:     return s",
                    ],
                },
            )
        },
    )
    result = run_generate(ctx)
    assert result.ok
    assert result.data["args"]["old_text"] == buggy
    assert (tmp_path / "sum_first.py").read_text(encoding="utf-8") == fixed


def test_generate_fix_bug_blocks_tests_path_before_run_tool(tmp_path):
    """fix_bug 写前拦截 tests/，不得调用 run_tool。"""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    original = "assert True\n"
    (tests_dir / "test_x.py").write_text(original, encoding="utf-8")
    (tmp_path / "foo.py").write_text("x = 1\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            '<tool>{"name":"patch_file","args":{"path":"tests/test_x.py",'
            '"new_text":"assert False"}}</tool>',
        ],
    )
    run_tool_calls: list[tuple[str, dict]] = []
    original_run_tool = agent.run_tool

    def tracking_run_tool(name, args):
        run_tool_calls.append((name, args))
        return original_run_tool(name, args)

    agent.run_tool = tracking_run_tool
    dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message="pytest fail",
        node_outputs={
            "locate": NodeResult(
                ok=True,
                message="ok",
                data={
                    "files": ["foo.py"],
                    "snippets": ["# file: foo.py L1-L1\n   1: x = 1"],
                },
            )
        },
    )
    result = run_generate(ctx)

    assert not result.ok
    assert result.data.get("policy_block") is True
    assert "禁止修改测试文件" in result.message
    assert run_tool_calls == []
    assert (tests_dir / "test_x.py").read_text(encoding="utf-8") == original
