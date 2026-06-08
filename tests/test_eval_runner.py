import json
from pathlib import Path

import pytest

from eval.run_eval import (
    check_expect_files,
    check_ollama_available,
    check_task_grading,
    compute_passed,
    format_compare_report,
    format_report_json,
    format_report_markdown,
    infer_failure_type,
    load_baseline,
    load_tasks,
    parse_harness_steps,
    resolve_task_grading,
    save_baseline,
    setup_task_workspace,
    task_result_to_dict,
    TaskResult,
)
from mini_coding_agent.platform.wait_display import set_wait_display_enabled

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "eval" / "tasks.json"


@pytest.fixture(autouse=True)
def _disable_wait_display():
    set_wait_display_enabled(False)
    yield
    set_wait_display_enabled(True)


def test_load_tasks_has_fix_bug_suite():
    tasks = load_tasks(TASKS_PATH)
    ids = [t["id"] for t in tasks]
    easy = [t for t in tasks if t.get("tier") == "easy"]
    assert len(easy) >= 12
    assert len(tasks) >= 15
    for tid in (
        "nameerror_calc",
        "syntaxerror_paren",
        "nameerror_greet",
        "off_by_one_sum",
        "wrong_operator_calc",
        "importerror_sqrt",
        "missing_return_abs",
        "wrong_comparison_max",
        "syntaxerror_colon",
        "nameerror_index",
        "off_by_one_range",
        "empty_body_double",
        "no_file_hint_add",
        "import_chain_rate",
        "logic_median_even",
    ):
        assert tid in ids
    assert all(t["harness_intent"] == "fix_bug" for t in tasks)


def test_setup_task_workspace_writes_files(tmp_path):
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    setup_task_workspace(tmp_path, task)
    assert (tmp_path / "calc.py").read_text(encoding="utf-8") == task["setup_files"]["calc.py"]


def test_report_contains_task_id_and_status():
    results = [
        TaskResult(task_id="nameerror_calc", passed=True, elapsed_ms=100.0),
        TaskResult(
            task_id="fail_task",
            passed=False,
            failure_step="generate",
            reason="mock",
            elapsed_ms=200.0,
        ),
    ]
    md = format_report_markdown(results)
    assert "nameerror_calc" in md
    assert "pass" in md
    assert "fail" in md


def test_check_ollama_available_missing_host():
    err = check_ollama_available(
        "http://127.0.0.1:59999",
        "no-such-model",
        timeout=2,
    )
    assert err is not None
    assert "Ollama" in err or "连接" in err


def test_tasks_migrated_tier_and_grading():
    tasks = load_tasks(TASKS_PATH)
    easy = [t for t in tasks if t.get("tier") == "easy"]
    medium = [t for t in tasks if t.get("tier") == "medium"]
    assert len(easy) >= 12
    assert len(medium) >= 3


def test_resolve_task_grading_defaults():
    assert resolve_task_grading({"expect_files": {"a.py": "x"}}) == "exact"
    assert resolve_task_grading({"verify": "pytest"}) == "tests_only"
    assert resolve_task_grading({"grading": "tests_only", "expect_files": {"a.py": "x"}}) == "tests_only"


def test_tests_only_passes_without_expect_match(tmp_path):
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "off_by_one_sum")
    setup_task_workspace(tmp_path, task)
    alt_fix = (
        "def sum_first(n):\n"
        "    s = 0\n"
        "    i = 1\n"
        "    while i <= n:\n"
        "        s += i\n"
        "        i += 1\n"
        "    return s\n"
    )
    (tmp_path / "sum_first.py").write_text(alt_fix, encoding="utf-8")
    assert check_expect_files(tmp_path, task["expect_files"]) is not None
    err, _ = check_task_grading(tmp_path, task)
    assert err is None


def test_exact_requires_expect_files_match(tmp_path):
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    setup_task_workspace(tmp_path, task)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b + 0\n", encoding="utf-8")
    err, step = check_task_grading(tmp_path, task)
    assert err is not None
    assert step == "expect_files"


def test_medium_no_file_hint_message_has_no_traceback_path():
    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "no_file_hint_add")
    assert 'File "' not in task["message"]
    assert ".py" not in task["message"]


def test_parse_harness_steps_from_stderr():
    stderr = (
        '[gate] intent_id=fix_bug confidence=high route=harness_pipeline skill=（无）\n'
        "[harness] fix_bug 1/3 locate ok\n"
        "[harness] fix_bug 2/3 generate fail\n"
    )
    steps = parse_harness_steps(stderr)
    assert [s["step"] for s in steps] == ["gate", "locate", "generate"]
    assert steps[2]["status"] == "fail"


def test_save_and_load_baseline(tmp_path):
    results = [
        TaskResult(task_id="a", passed=True, elapsed_ms=1.0),
        TaskResult(task_id="b", passed=False, failure_step="verify", elapsed_ms=2.0),
    ]
    path = tmp_path / "live.json"
    save_baseline(path, results, model="test-model")
    data = load_baseline(path)
    assert data["mode"] == "live"
    assert data["model"] == "test-model"
    assert data["summary"]["total"] == 2


def test_format_compare_report_detects_regression(tmp_path):
    results = [
        TaskResult(task_id="a", passed=True, elapsed_ms=1.0),
        TaskResult(task_id="b", passed=True, elapsed_ms=2.0),
    ]
    path = tmp_path / "base.json"
    save_baseline(path, results, model="m")
    regressed = [
        TaskResult(task_id="a", passed=False, failure_step="verify", reason="mock", elapsed_ms=1.0),
        TaskResult(task_id="b", passed=True, elapsed_ms=2.0),
    ]
    report = format_compare_report(regressed, path)
    assert "新增失败" in report
    assert "a" in report


def test_format_report_json_includes_steps():
    result = TaskResult(
        task_id="x",
        passed=True,
        elapsed_ms=1.0,
        steps=[{"step": "locate", "status": "ok", "detail": ""}],
    )
    payload = json.loads(format_report_json([result]))
    assert payload["tasks"][0]["steps"]
    assert task_result_to_dict(result)["passed"] is True


def test_main_preflight_failure_returns_2(monkeypatch):
    """Ollama 预检失败时 exit 2。"""
    from eval.run_eval import main

    monkeypatch.setattr(
        "eval.run_eval.check_ollama_available",
        lambda *args, **kwargs: "无法连接 Ollama（mock）",
    )
    assert main([]) == 2


def test_infer_failure_type_gate_low():
    session = {"last_gate": {"route": "open", "confidence": "low", "intent_id": "fix_bug"}}
    task = {"architecture": {"gate": {"route": "harness_pipeline"}}}
    assert infer_failure_type(session, "", None, task) == "gate_low"


def test_infer_failure_type_patch_match():
    stderr = "old_text 恰好出现 1 次，实际出现 0 次"
    assert infer_failure_type({}, stderr, None, {}) == "generate_patch_match"


def test_infer_failure_type_verify_pytest():
    assert infer_failure_type({}, "", "pytest 失败：assert 1 == 2", {}) == "verify_pytest"


def test_infer_failure_type_fallback_open():
    assert infer_failure_type({}, "流水线失败，降级 open", None, {}) == "fallback_open"


def test_infer_failure_type_locate_wrong_file(tmp_path):
    task = {
        "architecture": {"must_modify": ["calc.py"]},
        "setup_files": {"calc.py": "x = 1\n"},
    }
    setup_task_workspace(tmp_path, task)
    assert (
        infer_failure_type(
            {},
            "",
            "内容与期望不符",
            task,
            outcome_ok=False,
            workspace=tmp_path,
        )
        == "expect_files"
    )
    task2 = {
        "architecture": {"must_modify": ["calc.py"]},
        "setup_files": {"calc.py": "x = 1\n"},
    }
    setup_task_workspace(tmp_path, task2)
    assert (
        infer_failure_type(
            {},
            "",
            None,
            task2,
            outcome_ok=False,
            workspace=tmp_path,
        )
        == "locate_wrong_file"
    )


def test_task_result_to_dict_new_fields():
    result = TaskResult(
        task_id="x",
        passed=True,
        pipeline_ok=True,
        outcome_ok=True,
        failure_type="pipeline_ok",
        observability={"gate": {"route": "harness_pipeline"}},
        elapsed_ms=1.0,
    )
    data = task_result_to_dict(result)
    assert data["pipeline_ok"] is True
    assert data["outcome_ok"] is True
    assert data["failure_type"] == "pipeline_ok"
    assert data["observability"]["gate"]["route"] == "harness_pipeline"


def test_compute_passed_strict_pipeline():
    assert compute_passed(True, True, False) is True
    assert compute_passed(True, False, False) is True
    assert compute_passed(True, False, False, strict_pipeline=True) is False
    assert compute_passed(True, None, False, strict_pipeline=True) is True
    assert compute_passed(True, True, True) is False


def test_format_report_failure_type_aggregate():
    results = [
        TaskResult(
            task_id="a",
            passed=False,
            failure_type="generate_patch_match",
            outcome_ok=False,
        ),
        TaskResult(
            task_id="b",
            passed=False,
            failure_type="generate_patch_match",
            outcome_ok=False,
        ),
        TaskResult(
            task_id="c",
            passed=False,
            failure_type="gate_low",
            outcome_ok=False,
        ),
    ]
    md = format_report_markdown(results)
    assert "架构痛点聚合（failure_type）" in md
    assert "generate_patch_match" in md
    assert "建议优先改动" in md
    payload = json.loads(format_report_json(results))
    assert payload["summary"]["failure_types"]["generate_patch_match"] == 2


@pytest.mark.integration
def test_run_single_task_live_optional():
    """本机有 Ollama 时可选手动集成测；CI 默认 skip。"""
    from eval.run_eval import check_ollama_available, run_single_task
    from mini_coding_agent.platform.models import OllamaModelClient

    if check_ollama_available("http://127.0.0.1:11434", "qwen2.5-coder:7b", timeout=3):
        pytest.skip("Ollama 不可用")

    tasks = load_tasks(TASKS_PATH)
    task = next(t for t in tasks if t["id"] == "nameerror_calc")
    client = OllamaModelClient(model="qwen2.5-coder:7b", timeout=180)
    result = run_single_task(task, model_client=client, max_new_tokens=512)
    assert result.steps
    assert result.task_id == "nameerror_calc"
