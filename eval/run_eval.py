#!/usr/bin/env python3
"""黄金闭环 eval：隔离临时仓库 → handle_ask(harness) → Ollama 真实模型 → 断言与报告。"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from eval.task_schema import (  # noqa: E402
    apply_harness_contract_hints,
    assert_pipeline_contract,
    count_generate_attempts,
    diff_changed_files,
    node_outputs_from_session,
)
from mini_coding_agent import MiniAgent, SessionStore, WorkspaceContext  # noqa: E402
from mini_coding_agent.modes.graph.runner import handle_ask  # noqa: E402
from mini_coding_agent.modes.graph.verify_rules import (  # noqa: E402
    check_lock_tests_from_setup,
    run_task_verify,
)
from mini_coding_agent.platform.models import OllamaModelClient  # noqa: E402
from mini_coding_agent.platform.wait_display import set_wait_display_enabled  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_TASKS_PATH = EVAL_DIR / "tasks.json"


def ensure_eval_lock_tests_env() -> None:
    """eval 进程默认锁定 tests/；CLI 不设此变量则 lock_tests 关闭。"""
    os.environ.setdefault("HARNESS_LOCK_TESTS", "1")

_HARNESS_STEP = re.compile(
    r"\[harness\]\s+\S+\s+\d+/\d+\s+(\w+)\s+(ok|fail)",
    re.IGNORECASE,
)
_GATE_LINE = re.compile(
    r"\[gate\]\s+intent_id=(\S+)\s+confidence=(\S+)\s+route=(\S+)",
)

_FAILURE_TYPE_FIX_HINTS: dict[str, str] = {
    "gate_low": "mini_coding_agent/modes/graph/gate.py",
    "gate_wrong_intent": "mini_coding_agent/modes/graph/gate.py",
    "locate_no_snippet": "mini_coding_agent/modes/graph/nodes/locate.py",
    "locate_wrong_file": "mini_coding_agent/modes/graph/nodes/locate.py",
    "generate_protocol": "mini_coding_agent/platform/protocol.py",
    "generate_patch_match": "mini_coding_agent/modes/graph/nodes/generate.py",
    "generate_governance": "mini_coding_agent/platform/governance.py",
    "verify_lock_tests": "mini_coding_agent/modes/graph/verify_rules.py",
    "fallback_open": "mini_coding_agent/modes/graph/runner.py + 上游节点",
    "verify_py_compile": "nodes/generate.py / nodes/verify.py",
    "verify_pytest": "nodes/generate.py / nodes/verify.py",
    "expect_files": "任务设计 / generate",
    "exception": "调用栈",
}


@dataclass
class TaskResult:
    task_id: str
    passed: bool
    pipeline_ok: bool | None = None
    outcome_ok: bool = False
    failure_type: str | None = None
    observability: dict = field(default_factory=dict)
    failure_step: str | None = None
    reason: str | None = None
    elapsed_ms: float = 0.0
    harness_stderr: str = field(default="", repr=False)
    steps: list[dict] = field(default_factory=list)
    tier: str | None = None
    grading: str | None = None


def parse_harness_steps(stderr: str) -> list[dict]:
    """从 harness stderr 解析分步结果（gate / locate / generate / verify）。"""
    steps: list[dict] = []
    for line in (stderr or "").splitlines():
        gate = _GATE_LINE.search(line)
        if gate:
            steps.append(
                {
                    "step": "gate",
                    "status": "ok" if gate.group(3) == "harness_pipeline" else "fail",
                    "detail": (
                        f"intent_id={gate.group(1)} "
                        f"confidence={gate.group(2)} route={gate.group(3)}"
                    ),
                },
            )
            continue
        match = _HARNESS_STEP.search(line)
        if match:
            steps.append(
                {
                    "step": match.group(1).lower(),
                    "status": match.group(2).lower(),
                    "detail": line.strip(),
                },
            )
    return steps


def task_result_to_dict(result: TaskResult) -> dict:
    """TaskResult → 可 JSON 序列化的字典。"""
    return {
        "task_id": result.task_id,
        "passed": result.passed,
        "pipeline_ok": result.pipeline_ok,
        "outcome_ok": result.outcome_ok,
        "failure_type": result.failure_type,
        "observability": result.observability,
        "failure_step": result.failure_step,
        "reason": result.reason,
        "elapsed_ms": round(result.elapsed_ms, 1),
        "steps": result.steps,
        "tier": result.tier,
        "grading": result.grading,
    }


def build_observability(agent: MiniAgent, stderr: str) -> dict:
    """handle_ask 后从 session + stderr 组装 observability。"""
    session = agent.session
    trace = session.get("harness_trace")
    return {
        "gate": session.get("last_gate"),
        "last_verify": session.get("last_verify"),
        "harness_last_node": session.get("harness_last_node"),
        "files_touched": list(session.get("last_files_touched") or []),
        "open_fallback": "降级 open" in (stderr or ""),
        "generate_attempts": count_generate_attempts(stderr),
        "stage_trace": list(trace) if isinstance(trace, list) else [],
    }


def compute_passed(
    outcome_ok: bool,
    pipeline_ok: bool | None,
    open_fallback: bool,
    *,
    strict_pipeline: bool = False,
) -> bool:
    if open_fallback:
        return False
    if strict_pipeline and pipeline_ok is not None:
        return outcome_ok and pipeline_ok
    return outcome_ok


def infer_failure_type(
    session: dict,
    stderr: str,
    grading_err: str | None,
    task: dict,
    *,
    outcome_ok: bool = False,
    pipeline_ok: bool | None = None,
    workspace: Path | None = None,
    exception_occurred: bool = False,
) -> str:
    """按 04-failure-taxonomy.md §3 顺序推断 failure_type。"""
    if exception_occurred:
        return "exception"

    gate = session.get("last_gate") or {}
    arch = task.get("architecture") or {}
    arch_gate = arch.get("gate")
    text = stderr or ""

    if arch_gate:
        if gate.get("route") == "open" or gate.get("confidence") == "low":
            return "gate_low"
        if arch_gate.get("intent_id") and gate.get("intent_id") != arch_gate["intent_id"]:
            return "gate_wrong_intent"
    elif "route=open" in text and "fix_bug" in str(task.get("message", "")):
        return "gate_low"

    if "降级 open" in text:
        return "fallback_open"

    if grading_err:
        if "内容与期望不符" in grading_err or "缺少期望文件" in grading_err:
            return "expect_files"
        if "测试文件" in grading_err or "禁止修改测试" in grading_err:
            return "verify_lock_tests"
        if "pytest" in grading_err:
            return "verify_pytest"
        if "py_compile" in grading_err:
            return "verify_py_compile"

    if "generate 须返回 tool" in text:
        return "generate_protocol"
    if "old_text 恰好出现" in text and "实际出现 0" in text:
        return "generate_patch_match"
    if "old_text 恰好出现" in text and re.search(r"实际出现 [2-9]", text):
        return "generate_patch_match"
    if any(kw in text for kw in ("治理", "checkpoint", "approval")) and "拒绝" in text:
        return "generate_governance"
    if "locate：无有效源码 snippet" in text or "locate fail" in text:
        return "locate_no_snippet"
    if "verify fail" in text and "pytest" in text:
        return "verify_pytest"
    if "verify fail" in text and "py_compile" in text:
        return "verify_py_compile"

    if arch.get("must_modify") and workspace is not None:
        changed = diff_changed_files(workspace, task.get("setup_files") or {})
        if not all(f in changed for f in arch["must_modify"]):
            return "locate_wrong_file"

    if outcome_ok and pipeline_ok:
        return "pipeline_ok"
    if outcome_ok:
        return "outcome_ok"

    return "unknown"


def save_baseline(
    path: Path,
    results: list[TaskResult],
    *,
    model: str,
) -> None:
    """将本次 eval 结果写入基线 JSON。"""
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live",
        "model": model,
        "summary": {
            "passed": sum(1 for r in results if r.passed),
            "total": len(results),
        },
        "tasks": [task_result_to_dict(r) for r in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> dict:
    """加载基线 JSON。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "tasks" not in data:
        raise ValueError(f"基线格式无效：{path}")
    return data


def format_compare_report(current: list[TaskResult], baseline_path: Path) -> str:
    """对比当前结果与基线，输出回归摘要 Markdown。"""
    baseline = load_baseline(baseline_path)
    base_by_id = {t["task_id"]: t for t in baseline.get("tasks", [])}
    cur_by_id = {r.task_id: r for r in current}

    new_fail: list[str] = []
    recovered: list[str] = []
    still_fail: list[str] = []
    new_tasks: list[str] = []
    removed: list[str] = []

    for tid, cur in cur_by_id.items():
        base = base_by_id.get(tid)
        if base is None:
            new_tasks.append(tid)
            continue
        if base.get("passed") and not cur.passed:
            new_fail.append(tid)
        elif not base.get("passed") and cur.passed:
            recovered.append(tid)
        elif not base.get("passed") and not cur.passed:
            still_fail.append(tid)

    for tid in base_by_id:
        if tid not in cur_by_id:
            removed.append(tid)

    lines = [
        "# Eval 基线对比",
        "",
        f"**基线文件**：`{baseline_path}`",
        f"**基线时间**：{baseline.get('saved_at', '—')}",
        f"**基线模型**：{baseline.get('model', '—')}",
        f"**基线通过率**：{baseline.get('summary', {}).get('passed', '?')}"
        f"/{baseline.get('summary', {}).get('total', '?')}",
        f"**当前通过率**：{sum(1 for r in current if r.passed)}/{len(current)}",
        "",
    ]
    if new_fail:
        lines.extend(["## 新增失败（回归）", ""] + [f"- `{t}`" for t in new_fail] + [""])
    if recovered:
        lines.extend(["## 恢复通过", ""] + [f"- `{t}`" for t in recovered] + [""])
    if still_fail:
        lines.extend(["## 仍失败", ""] + [f"- `{t}`" for t in still_fail] + [""])
    if new_tasks:
        lines.extend(["## 基线中无（新任务）", ""] + [f"- `{t}`" for t in new_tasks] + [""])
    if removed:
        lines.extend(["## 当前未跑（基线有）", ""] + [f"- `{t}`" for t in removed] + [""])
    if not any((new_fail, recovered, still_fail, new_tasks, removed)):
        lines.append("**无差异**（任务集与通过情况一致）。")
    return "\n".join(lines) + "\n"


def load_tasks(path: Path | None = None) -> list[dict]:
    """加载 tasks.json。"""
    tasks_path = path or DEFAULT_TASKS_PATH
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"tasks.json 须为数组：{tasks_path}")
    return data


def resolve_task_grading(task: dict) -> str:
    """live 终判统一 tests_only；grading: exact 为遗留别名。"""
    explicit = task.get("grading")
    if explicit in ("exact", "tests_only"):
        return "tests_only"
    return "tests_only"


def setup_task_workspace(root: Path, task: dict) -> None:
    """写入 setup_files 与 Workspace 所需 README。"""
    (root / "README.md").write_text("eval workspace\n", encoding="utf-8")
    for rel_path, content in (task.get("setup_files") or {}).items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def build_eval_agent(
    root: Path,
    *,
    model_client: OllamaModelClient,
    max_new_tokens: int = 512,
) -> MiniAgent:
    """构建 eval 用 Agent：approval=auto、关闭 trace hook。"""
    workspace = WorkspaceContext.build(root)
    store = SessionStore(root / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=model_client,
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        enable_trace_hook=False,
        max_new_tokens=max_new_tokens,
    )


def check_expect_files(root: Path, expect_files: dict) -> str | None:
    """精确匹配 expect_files；失败返回原因。"""
    for rel_path, expected in expect_files.items():
        full = root / rel_path
        if not full.is_file():
            return f"缺少期望文件：{rel_path}"
        actual = full.read_text(encoding="utf-8")
        if actual != expected:
            return f"{rel_path} 内容与期望不符"
    return None


def check_task_verify(root: Path, verify: str) -> str | None:
    """任务级 verify（与 harness verify 节点共用规则）。"""
    return run_task_verify(root, verify)


def check_lock_tests(root: Path, task: dict) -> str | None:
    """含 tests/ 的任务：setup_files 中测试路径内容不得变。"""
    setup = task.get("setup_files") or {}
    if not any(str(p).replace("\\", "/").startswith("tests/") for p in setup):
        return None
    if task.get("lock_tests") is False:
        return None
    return check_lock_tests_from_setup(root, setup)


def check_task_grading(root: Path, task: dict) -> tuple[str | None, str | None]:
    """按 grading 终判；返回 (error, failure_step_hint)。"""
    grading = resolve_task_grading(task)

    lock_err = check_lock_tests(root, task)
    if lock_err:
        return lock_err, "lock_tests"

    verify_err = check_task_verify(root, task.get("verify", "none"))
    if verify_err:
        return verify_err, "verify"

    return None, None


def infer_failure_step(stderr: str, *, expect_error: str | None = None) -> str:
    """根据 stderr / 断言错误推断失败环节。"""
    if expect_error:
        if "内容与期望不符" in expect_error or "缺少期望文件" in expect_error:
            return "expect_files"
        if "测试文件" in expect_error or "禁止修改测试" in expect_error:
            return "lock_tests"
        if "py_compile" in expect_error or "pytest" in expect_error:
            return "verify"
        return "post_check"

    text = stderr or ""
    if "confidence=low" in text or "[gate]" in text and "route=open" in text:
        return "gate"
    if "locate fail" in text or "1/3 locate" in text:
        return "locate"
    if "generate 须返回 tool" in text or "generate 仅允许" in text:
        return "generate"
    if "verify fail" in text or " verify fail" in text or "/3 verify" in text:
        return "verify"
    if "py_compile 失败" in text:
        return "verify"
    if "流水线失败" in text or "降级 open" in text:
        return "pipeline"
    return "unknown"


def _stderr_excerpt(stderr: str, limit: int = 600) -> str:
    text = (stderr or "").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def check_ollama_available(host: str, model: str, *, timeout: int = 10) -> str | None:
    """预检 Ollama；失败返回中文原因，成功返回 None。"""
    base = host.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return (
            f"无法连接 Ollama（{base}）。请先运行 `ollama serve`，并确认模型已 pull。\n"
            f"详情：{exc}"
        )
    names = [m.get("name", m.get("model", "")) for m in data.get("models", [])]
    if model not in names and not any(n.startswith(model.split(":")[0]) for n in names):
        return (
            f"未在 Ollama 中找到模型 {model!r}。"
            f" 已安装：{', '.join(names[:8]) or '（无）'}。"
            f" 可执行 `ollama pull {model}`。"
        )
    return None


def _finalize_task_result(
    *,
    task: dict,
    task_id: str,
    agent: MiniAgent,
    root: Path,
    stderr_text: str,
    answer: str,
    t0: float,
    exception_occurred: bool = False,
    exception_msg: str | None = None,
    strict_pipeline: bool = False,
) -> TaskResult:
    """handle_ask 后统一组装 TaskResult（observability / failure_type / passed）。"""
    steps = parse_harness_steps(stderr_text)
    observability = build_observability(agent, stderr_text)
    open_fallback = observability.get("open_fallback", False)

    grading_err: str | None = None
    step_hint: str | None = None
    if not exception_occurred:
        grading_err, step_hint = check_task_grading(root, task)
    outcome_ok = grading_err is None and not exception_occurred

    pipeline_ok: bool | None = None
    if task.get("architecture") and not exception_occurred:
        contract = assert_pipeline_contract(
            task,
            agent,
            stderr_text,
            root,
            node_outputs=node_outputs_from_session(agent.session),
        )
        pipeline_ok = contract.pipeline_ok

    failure_type = infer_failure_type(
        agent.session,
        stderr_text,
        grading_err,
        task,
        outcome_ok=outcome_ok,
        pipeline_ok=pipeline_ok,
        workspace=root,
        exception_occurred=exception_occurred,
    )

    if exception_occurred:
        failure_step = "exception"
        reason = exception_msg
        steps.append({"step": "exception", "status": "fail", "detail": exception_msg or ""})
    elif grading_err:
        failure_step = step_hint or infer_failure_step(stderr_text, expect_error=grading_err)
        reason = grading_err
        steps.append({"step": failure_step, "status": "fail", "detail": grading_err[:300]})
    elif open_fallback and not (answer and "已修复并通过验证" in answer):
        failure_step = infer_failure_step(stderr_text)
        reason = f"流水线降级 open；回答：{answer[:200]}"
        steps.append({"step": failure_step, "status": "fail", "detail": reason})
    elif answer.startswith("流水线失败："):
        failure_step = infer_failure_step(stderr_text)
        reason = answer
        steps.append({"step": failure_step or "pipeline", "status": "fail", "detail": reason[:300]})
    else:
        failure_step = None
        reason = None
        if outcome_ok:
            steps.append({"step": "post_check", "status": "ok", "detail": "终判通过"})

    passed = compute_passed(
        outcome_ok,
        pipeline_ok,
        open_fallback and not (answer and "已修复并通过验证" in answer),
        strict_pipeline=strict_pipeline,
    )

    elapsed = (time.perf_counter() - t0) * 1000
    return TaskResult(
        task_id=task_id,
        passed=passed,
        pipeline_ok=pipeline_ok,
        outcome_ok=outcome_ok,
        failure_type=failure_type,
        observability=observability,
        failure_step=failure_step,
        reason=reason,
        elapsed_ms=elapsed,
        harness_stderr=stderr_text,
        steps=steps,
        tier=task.get("tier"),
        grading=resolve_task_grading(task),
    )


def run_single_task(
    task: dict,
    *,
    model_client: OllamaModelClient,
    max_new_tokens: int = 512,
    strict_pipeline: bool = False,
) -> TaskResult:
    """在独立临时目录执行单条 eval 任务（真实 Ollama）。"""
    ensure_eval_lock_tests_env()
    task_id = str(task.get("id", "unknown"))
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"eval-{task_id}-") as tmp:
        root = Path(tmp)
        setup_task_workspace(root, task)
        agent = build_eval_agent(
            root,
            model_client=model_client,
            max_new_tokens=max_new_tokens,
        )
        apply_harness_contract_hints(agent, task)

        stderr_buf = io.StringIO()
        answer = ""
        exception_occurred = False
        exception_msg: str | None = None
        try:
            with contextlib.redirect_stderr(stderr_buf):
                answer = handle_ask(
                    agent,
                    str(task.get("message", "")),
                    harness_enabled=True,
                )
        except Exception as exc:
            exception_occurred = True
            exception_msg = str(exc)

        return _finalize_task_result(
            task=task,
            task_id=task_id,
            agent=agent,
            root=root,
            stderr_text=stderr_buf.getvalue(),
            answer=answer,
            t0=t0,
            exception_occurred=exception_occurred,
            exception_msg=exception_msg,
            strict_pipeline=strict_pipeline,
        )


def run_eval(
    tasks: list[dict],
    *,
    task_filter: str | None = None,
    model_client: OllamaModelClient,
    max_new_tokens: int = 512,
    strict_pipeline: bool = False,
) -> list[TaskResult]:
    """执行全部（或筛选后的）任务。"""
    selected = tasks
    if task_filter:
        selected = [t for t in tasks if t.get("id") == task_filter]
        if not selected:
            raise ValueError(f"未找到任务 id={task_filter!r}")

    return [
        run_single_task(
            task,
            model_client=model_client,
            max_new_tokens=max_new_tokens,
            strict_pipeline=strict_pipeline,
        )
        for task in selected
    ]


def _aggregate_failure_types(results: list[TaskResult]) -> dict[str, list[str]]:
    agg: dict[str, list[str]] = {}
    for r in results:
        ft = r.failure_type
        if not ft or ft in ("pipeline_ok", "outcome_ok"):
            continue
        agg.setdefault(ft, []).append(r.task_id)
    return agg


def _format_fix_suggestions(agg: dict[str, list[str]]) -> list[str]:
    ranked = sorted(agg.items(), key=lambda x: len(x[1]), reverse=True)
    lines: list[str] = []
    for i, (ft, tasks) in enumerate(ranked[:5], start=1):
        hint = _FAILURE_TYPE_FIX_HINTS.get(ft, "补 taxonomy / 日志")
        lines.append(f"{i}. `{hint}` — {len(tasks)} 条 {ft}")
    return lines


def _stage_trace_markdown(trace: list[dict]) -> list[str]:
    """将 stage_trace 格式化为 Markdown 小节。"""
    if not trace:
        return []
    lines = ["", "## 阶段追踪（input / output）", ""]
    for entry in trace:
        stage = entry.get("stage", "?")
        lines.append(f"### {stage}")
        if entry.get("meta"):
            lines.append(f"- meta: `{json.dumps(entry['meta'], ensure_ascii=False)}`")
        inp = entry.get("input")
        if inp is not None:
            lines.append("")
            lines.append("**input**")
            lines.append("```")
            lines.append(json.dumps(inp, ensure_ascii=False, indent=2))
            lines.append("```")
        out = entry.get("output")
        if out is not None:
            lines.append("")
            lines.append("**output**")
            lines.append("```")
            lines.append(json.dumps(out, ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")
    return lines


def format_report_markdown(results: list[TaskResult]) -> str:
    """Markdown 报告：task_id、pass/fail、failure_type、耗时。"""
    lines = [
        "# Eval 报告",
        "",
        "| 任务 | 结果 | failure_type | 失败环节 | 原因 | 耗时(ms) |",
        "|------|------|--------------|----------|------|----------|",
    ]
    for r in results:
        status = "pass" if r.passed else "fail"
        step = r.failure_step or "—"
        ft = r.failure_type or "—"
        reason = (r.reason or "—").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r.task_id} | {status} | {ft} | {step} | {reason} | {r.elapsed_ms:.0f} |",
        )
    passed = sum(1 for r in results if r.passed)
    outcome_ok_count = sum(1 for r in results if r.outcome_ok)
    contract_results = [r for r in results if r.pipeline_ok is not None]
    pipeline_ok_count = sum(1 for r in contract_results if r.pipeline_ok)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| 指标 | 值 |",
            "|------|-----|",
            f"| passed | {passed}/{len(results)} |",
            f"| outcome_ok | {outcome_ok_count}/{len(results)} |",
        ],
    )
    if contract_results:
        lines.append(
            f"| pipeline_ok（有契约任务） | {pipeline_ok_count}/{len(contract_results)} |",
        )
    failed = [r for r in results if not r.passed]
    if failed:
        lines.extend(["", "## 分步结果（失败任务）", ""])
        for r in failed:
            if r.steps:
                step_text = " → ".join(
                    f"{s['step']}:{s['status']}" for s in r.steps
                )
                lines.append(f"- **{r.task_id}**：{step_text}")
            elif r.harness_stderr:
                excerpt = _stderr_excerpt(r.harness_stderr).replace("\n", " ")
                lines.append(f"- **{r.task_id}**（{r.failure_step}）：`{excerpt[:400]}`")

    agg = _aggregate_failure_types(results)
    if agg:
        lines.extend(["", "## 架构痛点聚合（failure_type）", ""])
        lines.append("| failure_type | 数量 | 任务 |")
        lines.append("|--------------|------|------|")
        for ft, tasks in sorted(agg.items(), key=lambda x: len(x[1]), reverse=True):
            task_list = ", ".join(f"`{t}`" for t in tasks)
            lines.append(f"| {ft} | {len(tasks)} | {task_list} |")
        suggestions = _format_fix_suggestions(agg)
        if suggestions:
            lines.extend(["", "## 建议优先改动", ""] + suggestions)

    for r in results:
        trace = (r.observability or {}).get("stage_trace") or []
        if trace:
            lines.append(f"\n---\n\n## 任务 `{r.task_id}` 阶段追踪")
            lines.extend(_stage_trace_markdown(trace)[3:])

    return "\n".join(lines) + "\n"


def format_report_json(results: list[TaskResult]) -> str:
    """JSON 报告。"""
    contract_results = [r for r in results if r.pipeline_ok is not None]
    failure_types: dict[str, int] = {}
    for r in results:
        ft = r.failure_type
        if ft and ft not in ("pipeline_ok", "outcome_ok"):
            failure_types[ft] = failure_types.get(ft, 0) + 1
    payload = {
        "summary": {
            "passed": sum(1 for r in results if r.passed),
            "total": len(results),
            "outcome_ok": sum(1 for r in results if r.outcome_ok),
            "pipeline_ok": sum(1 for r in contract_results if r.pipeline_ok),
            "pipeline_ok_total": len(contract_results),
            "failure_types": failure_types,
        },
        "tasks": [task_result_to_dict(r) for r in results],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def format_report_csv(results: list[TaskResult]) -> str:
    """CSV 报告。"""
    lines = ["task_id,passed,failure_step,reason,elapsed_ms"]
    for r in results:
        reason = (r.reason or "").replace('"', '""')
        lines.append(
            f'{r.task_id},{r.passed},{r.failure_step or ""},"{reason}",{r.elapsed_ms:.0f}',
        )
    return "\n".join(lines) + "\n"


def _build_client(args: argparse.Namespace) -> OllamaModelClient:
    return OllamaModelClient(
        model=args.model,
        host=args.host,
        temperature=args.temperature,
        top_p=args.top_p,
        timeout=args.ollama_timeout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="黄金闭环 fix_bug eval（Ollama 真实模型）")
    parser.add_argument("--task", help="仅运行指定 task id")
    parser.add_argument(
        "--tasks",
        type=Path,
        default=DEFAULT_TASKS_PATH,
        help=f"任务清单路径（默认 {DEFAULT_TASKS_PATH}）",
    )
    parser.add_argument(
        "--report",
        choices=("markdown", "csv", "json"),
        default="markdown",
        help="报告格式（markdown / csv / json）",
    )
    parser.add_argument(
        "--save-baseline",
        type=Path,
        metavar="PATH",
        help="将本次结果保存为基线 JSON（用于后续 --compare）",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        metavar="PATH",
        help="与基线 JSON 对比并输出回归摘要",
    )
    parser.add_argument("--model", default="qwen2.5-coder:7b", help="Ollama 模型名")
    parser.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama API 地址")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", dest="top_p", type=float, default=0.9)
    parser.add_argument("--ollama-timeout", dest="ollama_timeout", type=int, default=120)
    parser.add_argument(
        "--max-new-tokens",
        dest="max_new_tokens",
        type=int,
        default=512,
        help="每次 LLM complete 的 num_predict 上限",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="跳过启动前的 Ollama 连通性检查",
    )
    parser.add_argument(
        "--strict-pipeline",
        action="store_true",
        help="passed 同时要求 pipeline_ok（有 architecture 的任务）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        metavar="PATH",
        help="将报告写入文件（同时仍打印到 stdout）",
    )
    args = parser.parse_args(argv)
    ensure_eval_lock_tests_env()

    if not args.skip_preflight:
        err = check_ollama_available(args.host, args.model)
        if err:
            print(err, file=sys.stderr)
            return 2

    set_wait_display_enabled(False)
    try:
        tasks = load_tasks(args.tasks)
        model_client = _build_client(args)
        results = run_eval(
            tasks,
            task_filter=args.task,
            model_client=model_client,
            max_new_tokens=args.max_new_tokens,
            strict_pipeline=args.strict_pipeline,
        )
    finally:
        set_wait_display_enabled(True)

    if args.save_baseline:
        save_baseline(args.save_baseline, results, model=args.model)

    if args.compare:
        print(format_compare_report(results, args.compare), end="")

    if args.report == "markdown":
        report = format_report_markdown(results)
    elif args.report == "csv":
        report = format_report_csv(results)
    else:
        report = format_report_json(results)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")

    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
