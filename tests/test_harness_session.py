import json

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.runner import handle_ask
from mini_coding_agent.modes.graph.session_ctx import (
    clear_harness_session,
    empty_harness_fields,
    ensure_harness_session_shape,
    get_harness_context,
)
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


def test_consecutive_asks_read_last_gate_from_session(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high"),
            _patch_new_text("def add(a, b):\n    return a + b\n"),
            _gate_json("explain", "high"),
            "<final>第二次说明。</final>",
        ],
    )
    handle_ask(agent, TRACEBACK.strip(), harness_enabled=True)
    first_gate = dict(agent.session["last_gate"])
    assert first_gate["intent_id"] == "fix_bug"

    prior = get_harness_context(agent.session)
    assert prior["last_gate"]["intent_id"] == "fix_bug"

    handle_ask(agent, "解释 calc.py", harness_enabled=True)
    assert agent.session["last_gate"]["intent_id"] == "explain"
    assert agent.session["last_gate"] != first_gate


def test_fix_bug_pipeline_sets_last_files_touched(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high"),
            _patch_new_text("def add(a, b):\n    return a + b\n"),
        ],
    )
    handle_ask(agent, TRACEBACK.strip(), harness_enabled=True)
    assert "calc.py" in agent.session["last_files_touched"]

    loaded = json.loads(agent.session_path.read_text(encoding="utf-8"))
    assert "calc.py" in loaded["last_files_touched"]


def test_fix_bug_pipeline_sets_last_verify(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high"),
            _patch_new_text("def add(a, b):\n    return a + b\n"),
        ],
    )
    handle_ask(agent, TRACEBACK.strip(), harness_enabled=True)
    assert agent.session["last_verify"] is not None
    assert agent.session["last_verify"]["ok"] is True


def test_reset_clears_harness_session_fields(tmp_path):
    agent = _build_agent(tmp_path, [])
    agent.session["last_gate"] = {"intent_id": "fix_bug", "confidence": "high", "route": "harness_pipeline"}
    agent.session["last_files_touched"] = ["calc.py"]
    agent.session["last_verify"] = {"ok": True, "method": "py_compile", "summary": "ok"}
    agent.session["harness_last_node"] = {"intent_id": "fix_bug", "node_id": "review", "type": "review", "ok": True}
    agent.session_store.save(agent.session)

    agent.reset()

    for key, value in empty_harness_fields().items():
        assert agent.session[key] == value


def test_ensure_harness_session_shape_on_old_session(tmp_path):
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    legacy = {
        "id": "legacy-1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "workspace_root": str(tmp_path),
        "history": [],
        "memory": {"task": "", "files": [], "notes": [], "plan": None, "loaded_skills": {}},
    }
    store.save(legacy)
    agent = MiniAgent.from_session(
        model_client=FakeModelClient([]),
        workspace=WorkspaceContext.build(tmp_path),
        session_store=store,
        session_id="legacy-1",
        enable_trace_hook=False,
    )
    ensure_harness_session_shape(agent.session)
    assert agent.session["last_files_touched"] == []
    assert agent.session["last_gate"] is None


def test_observe_post_node_records_harness_last_node(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("fix_bug", "high"),
            _patch_new_text("def add(a, b):\n    return a + b\n"),
        ],
    )
    handle_ask(agent, TRACEBACK.strip(), harness_enabled=True)
    node = agent.session.get("harness_last_node")
    assert node is not None
    assert node["intent_id"] == "fix_bug"
    assert node["type"] == "verify"


def test_clear_harness_session_helper():
    session = {
        "last_gate": {"intent_id": "x"},
        "last_files_touched": ["a.py"],
        "last_verify": {"ok": True},
        "harness_last_node": {"type": "locate"},
    }
    clear_harness_session(session)
    assert session == empty_harness_fields()
