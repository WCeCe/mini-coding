"""EV-1：harness verify 与 eval 终判对齐。"""

import json
from pathlib import Path

import pytest

from eval.run_eval import check_lock_tests, check_task_verify, setup_task_workspace
from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.modes.graph.executor import execute_dag
from mini_coding_agent.modes.graph.nodes.verify import run_verify
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.modes.graph.verify_rules import (
    collect_tests_snapshot,
    resolve_test_command,
    run_task_verify,
)
from mini_coding_agent.platform.wait_display import set_wait_display_enabled


def _gate_json(intent_id="fix_bug", confidence="high"):
    return json.dumps({"intent_id": intent_id, "confidence": confidence})


def _patch_tool(old, new, path):
    return (
        '<tool>{"name":"patch_file","args":'
        f'{{"path":"{path}","old_text":{json.dumps(old)},"new_text":{json.dumps(new)}}}'
        "}</tool>"
    )


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


def _setup_sum_task(tmp_path: Path, *, buggy: bool = True) -> None:
    loop = "for i in range(1, n):" if buggy else "for i in range(1, n + 1):"
    (tmp_path / "sum_first.py").write_text(
        f"def sum_first(n):\n    s = 0\n    {loop}\n        s += i\n    return s\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_sum.py").write_text(
        "from sum_first import sum_first\n\n"
        "def test_sum_first():\n    assert sum_first(3) == 6\n",
        encoding="utf-8",
    )


def _verify_ctx(tmp_path, path="sum_first.py") -> HarnessContext:
    agent = _build_agent(tmp_path, [])
    dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message="pytest fail",
        test_baseline=collect_tests_snapshot(tmp_path),
    )
    ctx.node_outputs["generate"] = NodeResult(ok=True, message="ok", data={"path": path})
    return ctx


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_resolve_test_command_when_tests_dir_exists(tmp_path):
    (tmp_path / "tests").mkdir()
    assert resolve_test_command(tmp_path) == "python -m pytest -q"


def test_wrong_fix_py_compile_ok_but_pytest_fails(tmp_path):
    _setup_sum_task(tmp_path, buggy=False)
    (tmp_path / "sum_first.py").write_text(
        (tmp_path / "sum_first.py").read_text(encoding="utf-8").replace(
            "range(1, n + 1)", "range(1, n + 2)"
        ),
        encoding="utf-8",
    )
    ctx = _verify_ctx(tmp_path)
    result = run_verify(ctx)
    assert result.ok is False
    assert result.data.get("method") == "shell"
    assert result.data.get("command") == "python -m pytest -q"


def test_correct_fix_with_tests_passes_verify(tmp_path):
    _setup_sum_task(tmp_path, buggy=True)
    (tmp_path / "sum_first.py").write_text(
        (tmp_path / "sum_first.py").read_text(encoding="utf-8").replace(
            "range(1, n)", "range(1, n + 1)"
        ),
        encoding="utf-8",
    )
    ctx = _verify_ctx(tmp_path)
    result = run_verify(ctx)
    assert result.ok is True
    assert result.data.get("method") == "shell"


def test_no_tests_dir_uses_py_compile(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    ctx = _verify_ctx(tmp_path, path="calc.py")
    assert ctx.dag.slots.test_command is None
    result = run_verify(ctx)
    assert result.ok is True
    assert result.data.get("method") == "py_compile"


def test_lock_tests_rejects_generate_patch_on_test_file(tmp_path):
    _setup_sum_task(tmp_path)
    ctx = _verify_ctx(tmp_path, path="tests/test_sum.py")
    result = run_verify(ctx)
    assert result.ok is False
    assert result.data.get("method") == "lock_tests"
    assert "禁止修改测试文件" in result.message


def test_lock_tests_rejects_modified_test_content(tmp_path):
    _setup_sum_task(tmp_path)
    baseline = collect_tests_snapshot(tmp_path)
    test_file = tmp_path / "tests/test_sum.py"
    test_file.write_text(test_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    ctx = _verify_ctx(tmp_path)
    ctx.test_baseline = baseline
    result = run_verify(ctx)
    assert result.ok is False
    assert result.data.get("method") == "lock_tests"
    assert "测试文件被修改" in result.message


def test_harness_e2e_wrong_fix_verify_fails(tmp_path):
    _setup_sum_task(tmp_path)
    agent = _build_agent(
        tmp_path,
        [
            _gate_json(),
            _patch_tool("for i in range(1, n):", "for i in range(1, n+2):", "sum_first.py"),
        ],
    )
    dag = plan("fix_bug", user_message="pytest fail", workspace_root=tmp_path)
    result = execute_dag(agent, dag, "pytest fail")
    assert result.ok is False
    verify = agent.session.get("last_verify")
    assert verify is not None
    assert verify["ok"] is False


def test_run_eval_lock_tests_detects_tampered_test(tmp_path):
    task = {
        "id": "tamper",
        "message": "fix",
        "setup_files": {
            "sum_first.py": "x = 1\n",
            "tests/test_sum.py": "def test_x():\n    assert True\n",
        },
        "expect_files": {"sum_first.py": "x = 2\n"},
        "verify": "pytest",
        "harness_intent": "fix_bug",
    }
    setup_task_workspace(tmp_path, task)
    (tmp_path / "tests/test_sum.py").write_text("def test_x():\n    assert False\n", encoding="utf-8")
    err = check_lock_tests(tmp_path, task)
    assert err is not None
    assert "测试文件被修改" in err


def test_run_task_verify_shared_with_eval(tmp_path):
    _setup_sum_task(tmp_path, buggy=True)
    err = run_task_verify(tmp_path, "pytest")
    assert err is not None
    assert "pytest 失败" in err

    _setup_sum_task(tmp_path, buggy=False)
    assert run_task_verify(tmp_path, "pytest") is None
    assert check_task_verify(tmp_path, "pytest") is None


def test_off_by_one_sum_grading_tests_only(tmp_path):
    from eval.run_eval import load_tasks, setup_task_workspace, check_task_grading

    tasks_path = Path(__file__).resolve().parent.parent / "eval" / "tasks.json"
    task = next(t for t in load_tasks(tasks_path) if t["id"] == "off_by_one_sum")
    assert task["grading"] == "tests_only"
    setup_task_workspace(tmp_path, task)
    _setup_sum_task(tmp_path, buggy=False)
    err, _ = check_task_grading(tmp_path, task)
    assert err is None
