import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.run_eval import (
    build_fake_outputs,
    check_ollama_available,
    format_report_csv,
    format_report_markdown,
    load_tasks,
    run_eval,
    run_single_task,
    setup_task_workspace,
)
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "eval" / "tasks.json"
RUN_EVAL = REPO_ROOT / "eval" / "run_eval.py"


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_load_tasks_has_fix_bug_suite():
    tasks = load_tasks(TASKS_PATH)
    ids = [t["id"] for t in tasks]
    assert 3 <= len(tasks) <= 5
    for tid in (
        "nameerror_calc",
        "syntaxerror_paren",
        "nameerror_greet",
        "off_by_one_sum",
        "wrong_operator_calc",
    ):
        assert tid in ids
    assert all(t["harness_intent"] == "fix_bug" for t in tasks)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    assert "calc.py" in task["setup_files"]


def test_build_fake_outputs_order():
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    outputs = build_fake_outputs(task)
    assert len(outputs) == 2
    gate = json.loads(outputs[0])
    assert gate["intent_id"] == "fix_bug"
    assert gate["confidence"] == "high"
    assert "patch_file" in outputs[1]


def test_run_single_task_nameerror_passes():
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    result = run_single_task(task, fake=True)
    assert result.passed, result.reason


def test_setup_task_workspace_writes_files(tmp_path):
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    setup_task_workspace(tmp_path, task)
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == task["setup_files"]["calc.py"]


def test_run_eval_all_fake_pass():
    tasks = load_tasks(TASKS_PATH)
    results = run_eval(tasks, fake=True)
    assert len(results) >= 1
    assert all(r.passed for r in results), [r for r in results if not r.passed]


def test_run_eval_task_filter():
    tasks = load_tasks(TASKS_PATH)
    results = run_eval(tasks, fake=True, task_filter="nameerror_calc")
    assert len(results) == 1
    assert results[0].task_id == "nameerror_calc"
    assert results[0].passed


def test_report_contains_task_id_and_status():
    tasks = load_tasks(TASKS_PATH)
    results = run_eval(tasks, fake=True)
    md = format_report_markdown(results)
    assert "nameerror_calc" in md
    assert "pass" in md
    csv_text = format_report_csv(results)
    assert "nameerror_calc" in csv_text


def test_run_eval_cli_fake_subprocess():
    proc = subprocess.run(
        [sys.executable, str(RUN_EVAL), "--fake"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "nameerror_calc" in proc.stdout
    assert "| pass |" in proc.stdout
    assert "5/5" in proc.stdout


def test_check_ollama_available_missing_host():
    err = check_ollama_available(
        "http://127.0.0.1:59999",
        "no-such-model",
        timeout=2,
    )
    assert err is not None
    assert "Ollama" in err or "连接" in err
