import json

import pytest

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.gate import classify_gate, parse_gate_response
from mini_coding_agent.modes.graph.gate_prompt import build_gate_prompt
from mini_coding_agent.modes.graph.runner import format_gate_log_line, handle_ask
from mini_coding_agent.modes.graph.types import INTENT_IDS
from mini_coding_agent.platform.wait_display import set_wait_display_enabled


def _gate_json(intent_id, confidence="high", skill=None):
    payload = {"intent_id": intent_id, "confidence": confidence}
    if skill is not None:
        payload["skill"] = skill
    return json.dumps(payload, ensure_ascii=False)


def _build_workspace(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    return WorkspaceContext.build(tmp_path)


def _build_agent(tmp_path, outputs, **kwargs):
    workspace = _build_workspace(tmp_path)
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


@pytest.mark.parametrize(
    "intent_id",
    sorted(INTENT_IDS),
)
def test_classify_gate_high_for_each_intent(tmp_path, intent_id):
    agent = _build_agent(tmp_path, [_gate_json(intent_id, "high")])
    result = classify_gate(agent.model_client, "用户请求")
    assert result.intent_id == intent_id
    assert result.confidence == "high"
    assert result.route == "harness_pipeline"


def test_classify_gate_low_routes_open(tmp_path):
    agent = _build_agent(tmp_path, [_gate_json("explain", "low")])
    result = classify_gate(agent.model_client, "随便聊聊")
    assert result.confidence == "low"
    assert result.route == "open"


def test_parse_gate_invalid_json_routes_open():
    result = parse_gate_response("not json at all")
    assert result.confidence == "low"
    assert result.route == "open"
    assert result.intent_id == ""


def test_parse_gate_invalid_intent_routes_open():
    result = parse_gate_response(_gate_json("add_test", "high"))
    assert result.confidence == "low"
    assert result.route == "open"
    assert result.intent_id == "add_test"


def test_parse_gate_accepts_fenced_json():
    raw = '说明文字\n```json\n{"intent_id":"fix_bug","confidence":"high"}\n```'
    result = parse_gate_response(raw)
    assert result.intent_id == "fix_bug"
    assert result.route == "harness_pipeline"


def test_gate_prompt_contains_boundary_examples():
    prompt = build_gate_prompt("run pytest please")
    assert "explain how login works and fix the bug" in prompt
    assert "please run pytest for me" in prompt
    for intent_id in INTENT_IDS:
        assert intent_id in prompt


def test_handle_ask_low_same_as_plain_ask(tmp_path):
    gate_then_final = [
        _gate_json("explain", "low"),
        "<final>解释完毕。</final>",
    ]
    agent_with_gate = _build_agent(tmp_path, list(gate_then_final))
    agent_plain = _build_agent(tmp_path, ["<final>解释完毕。</final>"])

    answer_gate = handle_ask(agent_with_gate, "什么意思", harness_enabled=True)
    answer_plain = agent_plain.ask("什么意思")

    assert answer_gate == answer_plain == "解释完毕。"
    assert agent_with_gate.session["last_gate"]["route"] == "open"


def test_handle_ask_off_skips_gate_llm(tmp_path):
    agent = _build_agent(tmp_path, ["<final>直接回答。</final>"])
    handle_ask(agent, "hello", harness_enabled=False, gate_log=False)
    assert len(agent.model_client.prompts) == 1
    assert "意图分类器" not in agent.model_client.prompts[0]


def test_gate_log_prints_to_stderr(tmp_path, capsys):
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("project_ops", "high"),
            "<final>完成。</final>",
        ],
    )
    handle_ask(agent, "跑 pytest", harness_enabled=False, gate_log=True)
    captured = capsys.readouterr()
    assert "[gate]" in captured.err
    assert "intent_id=project_ops" in captured.err


def test_last_gate_persisted_to_session_file(tmp_path):
    agent = _build_agent(
        tmp_path,
        [
            _gate_json("refactor", "high", skill="my-skill"),
            "<final>好。</final>",
        ],
    )
    handle_ask(agent, "重构模块", gate_log=True)
    loaded = json.loads(agent.session_path.read_text(encoding="utf-8"))
    assert loaded["last_gate"] == {
        "intent_id": "refactor",
        "confidence": "high",
        "route": "harness_pipeline",
        "skill": "my-skill",
    }


def test_format_gate_log_line():
    from mini_coding_agent.modes.graph.types import GateResult

    line = format_gate_log_line(
        GateResult(intent_id="generate_code", confidence="high", route="harness_pipeline")
    )
    assert "intent_id=generate_code" in line
    assert "confidence=high" in line
