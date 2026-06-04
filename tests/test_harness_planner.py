import json

import pytest

from mini_coding_agent.modes.graph.planner import list_template_intents, load_template, plan
from mini_coding_agent.modes.graph.slots import extract_files_hint, extract_symbols_hint
from mini_coding_agent.modes.graph.types import DEFAULT_OPS_ALLOWLIST, INTENT_IDS

TRACEBACK_SAMPLE = """
Traceback (most recent call last):
  File "src/auth/login.py", line 42, in authenticate
    user = fetch_user(name)
NameError: name 'fetch_user' is not defined
"""

EXPECTED_NODE_TYPES = {
    "generate_code": ["locate", "generate", "verify", "review"],
    "fix_bug": ["locate", "generate", "verify"],
    "refactor": ["locate", "plan", "generate", "verify", "review"],
    "explain": ["locate", "explain"],
    "project_ops": ["locate", "ops", "review"],
}


@pytest.mark.parametrize("intent_id", sorted(INTENT_IDS))
def test_template_loads_and_matches_filename(intent_id):
    template = load_template(intent_id)
    assert template["intent_id"] == intent_id
    assert template["nodes"]
    for node in template["nodes"]:
        assert node.id
        assert node.type


def test_all_templates_registered():
    assert set(list_template_intents()) == set(INTENT_IDS)


@pytest.mark.parametrize("intent_id", ("generate_code", "fix_bug"))
def test_coding_templates_have_verify_retry(intent_id):
    template = load_template(intent_id)
    assert "verify" in template["retry"]
    policy = template["retry"]["verify"]
    assert policy.on_fail == "generate"
    assert policy.max == 2


def test_refactor_template_has_plan_dependency():
    template = load_template("refactor")
    nodes = {node.id: node for node in template["nodes"]}
    assert "plan" in nodes
    assert nodes["plan"].type == "plan"
    assert nodes["plan"].deps == ["locate"]
    assert nodes["generate"].deps == ["plan"]


def test_explain_template_has_no_generate():
    template = load_template("explain")
    types = [node.type for node in template["nodes"]]
    assert "generate" not in types
    assert types == ["locate", "explain"]


def test_project_ops_template_has_no_write_path():
    template = load_template("project_ops")
    types = [node.type for node in template["nodes"]]
    assert "generate" not in types
    assert types == ["locate", "ops", "review"]


@pytest.mark.parametrize("intent_id", sorted(INTENT_IDS))
def test_plan_for_each_intent(tmp_path, intent_id):
    (tmp_path / "tests").mkdir()
    message = f"用户任务：{intent_id}"
    if intent_id == "fix_bug":
        message = TRACEBACK_SAMPLE

    dag = plan(
        intent_id,
        user_message=message,
        skill_name="demo-skill" if intent_id == "refactor" else None,
        workspace_root=tmp_path,
    )

    assert dag.intent_id == intent_id
    assert dag.node_types() == EXPECTED_NODE_TYPES[intent_id]
    assert dag.slots.goal
    assert dag.slots.test_command == "python -m pytest -q"

    if intent_id in ("generate_code", "fix_bug", "refactor"):
        assert dag.retry["verify"].on_fail == "generate"
        assert dag.retry["verify"].max == 2

    if intent_id == "refactor":
        assert dag.slots.skill_name == "demo-skill"

    if intent_id == "project_ops":
        assert dag.slots.ops_allowlist == list(DEFAULT_OPS_ALLOWLIST)

    if intent_id == "explain":
        assert "generate" not in dag.node_types()


def test_fix_bug_traceback_fills_files_hint(tmp_path):
    dag = plan(
        "fix_bug",
        user_message=TRACEBACK_SAMPLE,
        workspace_root=tmp_path,
    )
    assert "src/auth/login.py" in dag.slots.files_hint


def test_traceback_extracts_symbols():
    symbols = extract_symbols_hint(TRACEBACK_SAMPLE)
    assert "fetch_user" in symbols


def test_extract_files_hint_from_message():
    files = extract_files_hint("请修 auth/login.py 里的 bug")
    assert "auth/login.py" in files


def test_plan_rejects_unknown_intent():
    with pytest.raises(ValueError, match="不支持的 intent_id"):
        plan("add_test", user_message="hello")


def test_template_json_on_disk_matches_intent(tmp_path):
    from mini_coding_agent.modes.graph.planner import TEMPLATES_DIR

    for intent_id in INTENT_IDS:
        path = TEMPLATES_DIR / f"{intent_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["intent_id"] == intent_id
