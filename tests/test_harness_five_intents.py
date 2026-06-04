import json
from unittest.mock import patch

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.nodes.explain import assert_no_risky_tools
from mini_coding_agent.modes.graph.nodes.ops import command_is_allowlisted, infer_ops_command
from mini_coding_agent.modes.graph.runner import handle_ask
from mini_coding_agent.modes.graph.types import DEFAULT_OPS_ALLOWLIST, INTENT_IDS, PIPELINE_INTENTS_V1
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

TRACEBACK = """
Traceback (most recent call last):
  File "calc.py", line 2, in add
    return a + c
NameError: name 'c' is not defined
"""


def _gate_json(intent_id, confidence="high", skill=None):
    payload = {"intent_id": intent_id, "confidence": confidence}
    if skill is not None:
        payload["skill"] = skill
    return json.dumps(payload, ensure_ascii=False)


def _patch_tool(old, new, path="calc.py"):
    return (
        '<tool>{"name":"patch_file","args":'
        f'{{"path":"{path}","old_text":{json.dumps(old)},"new_text":{json.dumps(new)}}}'
        "}</tool>"
    )


def _write_tool(path, content):
    return (
        '<tool>{"name":"write_file","args":'
        f'{{"path":"{path}","content":{json.dumps(content)}}}'
        "}</tool>"
    )


def _sample_plan(goal="refactor module"):
    return json.dumps(
        {
            "goal": goal,
            "steps": [
                {"id": "1", "title": "Survey", "acceptance": "Files listed"},
                {"id": "2", "title": "Refactor", "acceptance": "Structure improved"},
            ],
            "assumptions": [],
            "out_of_scope": [],
        },
        ensure_ascii=False,
    )


def _write_skill(tmp_path, name):
    skill_dir = tmp_path / ".mini-coding-agent" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test skill\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def _build_agent(tmp_path, outputs, **kwargs):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=FakeModelClient(outputs),
        workspace=workspace,
        session_store=store,
        approval_policy=kwargs.pop("approval_policy", "auto"),
        enable_trace_hook=False,
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_pipeline_intents_covers_all_five():
    assert PIPELINE_INTENTS_V1 == INTENT_IDS


@pytest.mark.parametrize("intent_id", sorted(INTENT_IDS))
def test_high_intent_enters_pipeline_not_silent_open(tmp_path, intent_id, capsys):
    """五类 high 均走 pipeline（stderr 有 harness 进度，成功时不 ask）。"""
    (tmp_path / "calc.py").write_text("x = 1\n", encoding="utf-8")
    outputs = [_gate_json(intent_id, "high")]

    if intent_id == "fix_bug":
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
        outputs += [_patch_tool("return a + c", "return a + b")]
    elif intent_id == "generate_code":
        outputs += [
            _write_tool("hello.py", "def hello():\n    return 1\n"),
            "<final>generate ok</final>",
        ]
    elif intent_id == "refactor":
        outputs += [
            _sample_plan(),
            _patch_tool("x = 1", "x = 2"),
            "<final>refactor ok</final>",
        ]
    elif intent_id == "explain":
        outputs += ["<final>这是 calc.py 的说明。</final>"]
    elif intent_id == "project_ops":
        (tmp_path / "tests").mkdir(exist_ok=True)
        (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        outputs += ["<final>ops ok</final>"]

    agent = _build_agent(tmp_path, outputs)
    ask_calls = []
    agent.ask = lambda msg: ask_calls.append(msg) or "unexpected ask"

    message = {
        "fix_bug": TRACEBACK.strip(),
        "generate_code": "实现 hello.py 新函数",
        "refactor": "重构 calc.py",
        "explain": "解释 calc.py 怎么工作",
        "project_ops": "跑 pytest",
    }[intent_id]

    answer = handle_ask(agent, message, harness_enabled=True)
    captured = capsys.readouterr()

    assert not ask_calls
    assert f"[harness] {intent_id}" in captured.err
    assert answer


def test_explain_e2e_no_write_tools(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("explain", "high"),
            "<final>calc.py 实现加法。</final>",
        ],
    )
    risky = []
    original_run_tool = agent.run_tool

    def track_run_tool(name, args):
        if name in {"write_file", "patch_file", "run_shell"}:
            risky.append(name)
            assert_no_risky_tools(name)
        return original_run_tool(name, args)

    agent.run_tool = track_run_tool
    answer = handle_ask(agent, "解释 calc.py", harness_enabled=True)
    assert not risky
    assert "calc.py" in answer


def test_project_ops_e2e_whitelist_shell_only(tmp_path):
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("project_ops", "high"),
            "<final>pytest 已执行。</final>",
        ],
    )
    shell_calls = []
    write_calls = []
    original = agent.run_tool

    def track(name, args):
        if name == "run_shell":
            shell_calls.append(args.get("command", ""))
        if name in {"write_file", "patch_file"}:
            write_calls.append(name)
        return original(name, args)

    agent.run_tool = track
    answer = handle_ask(agent, "跑 pytest", harness_enabled=True)
    assert shell_calls
    assert command_is_allowlisted(shell_calls[0], list(DEFAULT_OPS_ALLOWLIST))
    assert not write_calls
    assert "pytest" in answer.lower() or "执行" in answer


def test_project_ops_rejects_non_allowlisted_command():
    assert not command_is_allowlisted("rm -rf /", list(DEFAULT_OPS_ALLOWLIST))
    assert infer_ops_command("删除所有文件 rm -rf") is None


def test_project_ops_node_fails_on_blocked_command(tmp_path):
    from mini_coding_agent.modes.graph.executor import execute_dag
    from mini_coding_agent.modes.graph.planner import plan

    agent = _build_agent(tmp_path, ["<final>noop</final>"])
    dag = plan("project_ops", user_message="恶意操作", workspace_root=tmp_path)

    with patch(
        "mini_coding_agent.modes.graph.nodes.ops.infer_ops_command",
        return_value="rm -rf /",
    ):
        result = execute_dag(agent, dag, "恶意操作")

    assert not result.ok
    assert "白名单" in result.reason


def test_gate_skill_preloads_before_pipeline(tmp_path):
    _write_skill(tmp_path, "code-review")
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high", skill="code-review"),
            _patch_tool("return a + c", "return a + b"),
            "<final>with skill</final>",
        ],
    )
    handle_ask(agent, TRACEBACK.strip(), harness_enabled=True)
    assert "code-review" in agent.session["memory"]["loaded_skills"]


def test_generate_code_e2e_writes_file(tmp_path):
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("generate_code", "high"),
            _write_tool("hello.py", "def hello():\n    return 42\n"),
            "<final>已创建 hello.py</final>",
        ],
    )
    handle_ask(agent, "实现 hello.py", harness_enabled=True)
    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "def hello():\n    return 42\n"


def test_refactor_e2e_runs_plan_then_generate(tmp_path):
    (tmp_path / "calc.py").write_text("x = 1\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("refactor", "high"),
            _sample_plan("refactor calc"),
            _patch_tool("x = 1", "x = 2"),
            "<final>重构完成</final>",
        ],
    )
    handle_ask(agent, "重构 calc.py", harness_enabled=True)
    assert agent.session["memory"]["plan"] is not None
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == "x = 2\n"
