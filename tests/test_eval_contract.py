"""L2 管线契约 eval：FakeModel + tasks.json architecture 断言。"""

import contextlib
import io
from pathlib import Path

import pytest

from eval.run_eval import build_eval_agent, check_task_grading, ensure_eval_lock_tests_env, setup_task_workspace
from eval.task_schema import (
    apply_harness_contract_hints,
    assert_pipeline_contract,
    fake_script_to_outputs,
    load_tasks,
    tasks_with_fake_script,
)
from mini_coding_agent.modes.graph.nodes.locate import run_locate
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.types import HarnessContext
from mini_coding_agent.index import default_db_path
from mini_coding_agent.modes.graph.runner import handle_ask
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "eval" / "tasks.json"

CONTRACT_TASK_IDS = tuple(
    t["id"] for t in tasks_with_fake_script(load_tasks(TASKS_PATH))
)


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


@pytest.fixture(autouse=True)
def _eval_lock_tests_like_live():
    """与 live eval 一致：lock_tests 开启（tasks.json lock_tests: true）。"""
    ensure_eval_lock_tests_env()


@pytest.mark.parametrize("task_id", CONTRACT_TASK_IDS)
def test_pipeline_contract_and_grading(task_id: str, tmp_path: Path):
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task.get("fake_script"), f"{task_id} 缺少 fake_script"
    assert task.get("architecture"), f"{task_id} 缺少 architecture"

    setup_task_workspace(tmp_path, task)

    if task_id == "bench_no_rig_search":
        assert not default_db_path(tmp_path).exists(), "B4 setup 须无 rig.db"

    outputs = fake_script_to_outputs(task["fake_script"])
    agent = build_eval_agent(tmp_path, model_client=FakeModelClient(outputs))
    apply_harness_contract_hints(agent, task)

    stderr_buf = io.StringIO()
    with contextlib.redirect_stderr(stderr_buf):
        handle_ask(agent, str(task["message"]), harness_enabled=True)
    stderr = stderr_buf.getvalue()

    contract = assert_pipeline_contract(task, agent, stderr, tmp_path)
    assert contract.pipeline_ok, "\n".join(contract.failures)

    grading_err, _ = check_task_grading(tmp_path, task)
    assert grading_err is None, grading_err


def test_architecture_locate_fails_without_valid_snippet(tmp_path: Path):
    """无 hint 且契约要求 min_snippets 时，locate 应 fail 而非拖到 generate。"""
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    agent = MiniAgent(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
    )
    dag = plan("fix_bug", user_message="请修复项目中的 bug", workspace_root=tmp_path)
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message="请修复项目中的 bug",
        locate_min_snippets_with_source_lines=1,
    )
    result = run_locate(ctx)
    assert result.ok is False
    assert result.message == "locate：无有效源码 snippet"


def test_bench_retry_fake_script_has_retry_buffer_outputs():
    """B1 retry：gate + 错误 patch + 正确 patch + 缓冲（policy_block 重试不挤占 verify 预算）。"""
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "bench_retry_off_by_one")
    outputs = fake_script_to_outputs(task["fake_script"])
    assert len(outputs) >= 4


def test_contract_suite_covers_all_bench_tasks():
    """P0-b 3 条 + P1-b B1–B4 四条 bench + B5(import_chain_rate) = 7 条 fake_script 契约。"""
    assert len(CONTRACT_TASK_IDS) == 7
    expected = {
        "nameerror_calc",
        "off_by_one_sum",
        "import_chain_rate",
        "bench_retry_off_by_one",
        "bench_decoy_calc_backup",
        "bench_gate_explain_boundary",
        "bench_no_rig_search",
    }
    assert set(CONTRACT_TASK_IDS) == expected
