import json
from unittest.mock import patch

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.executor import execute_dag
from mini_coding_agent.modes.graph.pipeline import run_pipeline, run_pipeline_dag
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.runner import handle_ask
from mini_coding_agent.modes.graph.types import NodeResult
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

TRACEBACK = """
Traceback (most recent call last):
  File "calc.py", line 2, in add
    return a + c
NameError: name 'c' is not defined
"""


def _gate_json(intent_id="fix_bug", confidence="high"):
    return json.dumps({"intent_id": intent_id, "confidence": confidence})


def _patch_tool(old, new, path="calc.py"):
    return (
        '<tool>{"name":"patch_file","args":'
        f'{{"path":"{path}","old_text":{json.dumps(old)},"new_text":{json.dumps(new)}}}'
        "}</tool>"
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


def test_fix_bug_e2e_harness_pipeline(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high"),
            _patch_tool("return a + c", "return a + b"),
        ],
    )
    ask_calls = []
    original_ask = agent.ask
    agent.ask = lambda msg: ask_calls.append(msg) or original_ask(msg)

    answer = handle_ask(
        agent,
        TRACEBACK.strip(),
        harness_enabled=True,
    )

    assert not ask_calls
    assert "已修复并通过验证" in answer
    assert "calc.py" in answer
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
    assert agent.session["last_gate"]["intent_id"] == "fix_bug"


def test_verify_retry_runs_generate_twice(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    bad_patch = _patch_tool("return a + c", "return a +")
    good_patch = _patch_tool("return a +", "return a + b")
    agent = _build_agent(
        tmp_path,
        [
            bad_patch,
            good_patch,
        ],
    )
    dag = plan("fix_bug", user_message=TRACEBACK, workspace_root=tmp_path)
    result = execute_dag(agent, dag, TRACEBACK)

    assert result.ok
    assert "已修复并通过验证" in result.final_text
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
    assert len(agent.model_client.prompts) == 2


def test_pipeline_failure_fallback_open(tmp_path):
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high"),
            "invalid model output without tool",
            "<final>open 降级回答。</final>",
        ],
    )
    answer = handle_ask(agent, TRACEBACK, harness_enabled=True)
    assert answer == "open 降级回答。"


def test_generate_uses_run_tool_governance(tmp_path):
    (tmp_path / "calc.py").write_text("x = 1\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _patch_tool("x = 1", "x = 2"),
        ],
        approval_policy="auto",
    )
    run_tool_calls = []
    original = agent.run_tool

    def tracking_run_tool(name, args):
        run_tool_calls.append((name, args))
        return original(name, args)

    agent.run_tool = tracking_run_tool
    dag = plan("fix_bug", user_message='File "calc.py"', workspace_root=tmp_path)
    result = run_pipeline_dag(agent, dag, 'File "calc.py"')

    assert result.ok
    assert any(name == "patch_file" for name, _ in run_tool_calls)
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == "x = 2\n"


def test_run_pipeline_integration(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _patch_tool("return a + c", "return a + b"),
        ],
    )
    result = run_pipeline(agent, "fix_bug", TRACEBACK)
    assert result.ok
    assert "已修复并通过验证" in result.final_text


def test_executor_verify_retry_via_mock(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _patch_tool("return a + c", "return a +"),
            _patch_tool("return a +", "return a + b"),
        ],
    )
    dag = plan("fix_bug", user_message=TRACEBACK, workspace_root=tmp_path)
    verify_calls = {"n": 0}
    from mini_coding_agent.modes.graph.nodes import verify as verify_mod

    real_verify = verify_mod.run_verify

    def counting_verify(ctx):
        verify_calls["n"] += 1
        if verify_calls["n"] == 1:
            return NodeResult(ok=False, message="mock verify fail")
        return real_verify(ctx)

    with patch.dict(
        "mini_coding_agent.modes.graph.executor.NODE_RUNNERS",
        {"verify": counting_verify},
    ):
        result = execute_dag(agent, dag, TRACEBACK)

    assert result.ok
    assert verify_calls["n"] == 2
    assert len(agent.model_client.prompts) == 2
