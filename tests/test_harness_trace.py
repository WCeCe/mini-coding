import json

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.runner import handle_ask
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

TRACEBACK = """
Traceback (most recent call last):
  File "calc.py", line 2, in add
    return a + c
NameError: name 'c' is not defined
"""


def _gate_json(intent_id="fix_bug", confidence="high"):
    return json.dumps({"intent_id": intent_id, "confidence": confidence})


def _patch_new_text(new, path="calc.py"):
    return (
        '<tool>{"name":"patch_file","args":'
        f'{{"path":"{path}","new_text":{json.dumps(new)}}}'
        "}</tool>"
    )


def test_handle_ask_records_stage_trace(tmp_path):
    set_wait_display_enabled(False)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    agent = MiniAgent(
        model_client=FakeModelClient(
            [
                _gate_json("fix_bug", "high"),
                _patch_new_text("def add(a, b):\n    return a + b\n"),
            ],
        ),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )

    handle_ask(agent, TRACEBACK.strip(), harness_enabled=True)

    trace = agent.session.get("harness_trace") or []
    stages = [entry["stage"] for entry in trace]
    assert stages == ["gate", "rig", "slots", "locate", "generate", "verify"]

    gate = trace[0]
    assert "prompt" in gate["input"]
    assert gate["input"]["user_message"].strip().startswith("Traceback")

    generate = next(entry for entry in trace if entry["stage"] == "generate")
    assert "prompt" in generate["input"]
    assert "定位上下文" in generate["input"]["prompt"]
    assert "raw" in generate["output"]
    assert generate["output"]["tool"] == "patch_file"

    locate = next(entry for entry in trace if entry["stage"] == "locate")
    assert "calc.py" in locate["output"]["files"]
