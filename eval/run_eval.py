#!/usr/bin/env python3
"""黄金闭环 eval：隔离临时仓库 → handle_ask(harness) → 断言与报告。"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import py_compile
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# 允许 `python eval/run_eval.py` 从仓库根导入 mini_coding_agent
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext  # noqa: E402
from mini_coding_agent.modes.graph.runner import handle_ask  # noqa: E402
from mini_coding_agent.platform.models import OllamaModelClient  # noqa: E402
from mini_coding_agent.platform.wait_display import set_wait_display_enabled  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_TASKS_PATH = EVAL_DIR / "tasks.json"


@dataclass
class TaskResult:
    task_id: str
    passed: bool
    failure_step: str | None = None
    reason: str | None = None
    elapsed_ms: float = 0.0
    harness_stderr: str = field(default="", repr=False)


def load_tasks(path: Path | None = None) -> list[dict]:
    """加载 tasks.json。"""
    tasks_path = path or DEFAULT_TASKS_PATH
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"tasks.json 须为数组：{tasks_path}")
    return data


def _gate_json(intent_id: str = "fix_bug", confidence: str = "high") -> str:
    return json.dumps({"intent_id": intent_id, "confidence": confidence}, ensure_ascii=False)


def _patch_tool(old_text: str, new_text: str, path: str = "calc.py") -> str:
    return (
        '<tool>{"name":"patch_file","args":'
        f'{{"path":"{path}","old_text":{json.dumps(old_text, ensure_ascii=False)},'
        f'"new_text":{json.dumps(new_text, ensure_ascii=False)}}}'
        "}</tool>"
    )


def _line_based_patch_snippet(old: str, new: str) -> tuple[str, str] | None:
    """字符级 diff 退化时，取首对不同的整行作为 patch。"""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    limit = max(len(old_lines), len(new_lines))
    for i in range(limit):
        o_line = old_lines[i] if i < len(old_lines) else ""
        n_line = new_lines[i] if i < len(new_lines) else ""
        if o_line != n_line:
            return o_line, n_line
    return None


def _extract_patch_snippet(old: str, new: str) -> tuple[str, str] | None:
    """从 setup/expect 全文推导 patch_file 的 old_text/new_text。"""
    if old == new:
        return None
    prefix = 0
    limit = min(len(old), len(new))
    while prefix < limit and old[prefix] == new[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(old) - prefix
        and suffix < len(new) - prefix
        and old[len(old) - 1 - suffix] == new[len(new) - 1 - suffix]
    ):
        suffix += 1
    old_mid = old[prefix : len(old) - suffix]
    new_mid = new[prefix : len(new) - suffix]
    if not old_mid and not new_mid:
        return None
    if len(old_mid) < 2 or (old_mid and not new_mid):
        line_snippet = _line_based_patch_snippet(old, new)
        if line_snippet:
            return line_snippet
    return old_mid, new_mid


def build_fake_outputs(task: dict) -> list[str]:
    """按任务推导 FakeModel 队列：Gate → Generate(patch)；verify 通过即成功（无 review）。"""
    intent = str(task.get("harness_intent", "fix_bug"))
    outputs: list[str] = [_gate_json(intent, "high")]

    setup = task.get("setup_files") or {}
    expect = task.get("expect_files") or {}
    for rel_path, expected in expect.items():
        old_content = setup.get(rel_path, "")
        snippet = _extract_patch_snippet(old_content, expected)
        if snippet:
            old_text, new_text = snippet
            outputs.append(_patch_tool(old_text, new_text, path=rel_path))

    return outputs


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
    fake_outputs: list[str] | None = None,
    model_client=None,
    max_new_tokens: int = 512,
) -> MiniAgent:
    """构建 eval 用 Agent：approval=auto、关闭 trace hook。"""
    workspace = WorkspaceContext.build(root)
    store = SessionStore(root / ".mini-coding-agent" / "sessions")
    client = model_client if model_client is not None else FakeModelClient(fake_outputs or [])
    return MiniAgent(
        model_client=client,
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
    """任务级 verify（与 harness 节点独立复核）。"""
    if verify in ("", "none", None):
        return None
    if verify == "py_compile":
        errors: list[str] = []
        for py_file in sorted(root.rglob("*.py")):
            if ".mini-coding-agent" in py_file.parts:
                continue
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"{py_file.relative_to(root)}: {exc}")
        if errors:
            return "py_compile 失败：\n" + "\n".join(errors)
        return None
    if verify == "pytest":
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            return f"pytest 失败（exit {proc.returncode}）：{detail[:500]}"
        return None
    return f"未知 verify 类型：{verify!r}"


def infer_failure_step(stderr: str, *, expect_error: str | None = None) -> str:
    """根据 stderr / 断言错误推断失败环节（对齐 golden-loop §7）。"""
    if expect_error:
        if "内容与期望不符" in expect_error or "缺少期望文件" in expect_error:
            return "expect_files"
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


def run_single_task(
    task: dict,
    *,
    fake: bool = True,
    model_client=None,
    max_new_tokens: int = 512,
) -> TaskResult:
    """在独立临时目录执行单条 eval 任务。"""
    task_id = str(task.get("id", "unknown"))
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"eval-{task_id}-") as tmp:
        root = Path(tmp)
        setup_task_workspace(root, task)

        if fake:
            outputs = build_fake_outputs(task)
            agent = build_eval_agent(root, fake_outputs=outputs, max_new_tokens=max_new_tokens)
        else:
            if model_client is None:
                return TaskResult(
                    task_id=task_id,
                    passed=False,
                    failure_step="config",
                    reason="非 Fake 模式须提供 model_client",
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                )
            agent = build_eval_agent(
                root,
                model_client=model_client,
                max_new_tokens=max_new_tokens,
            )

        stderr_buf = io.StringIO()
        answer = ""
        try:
            with contextlib.redirect_stderr(stderr_buf):
                answer = handle_ask(
                    agent,
                    str(task.get("message", "")),
                    harness_enabled=True,
                )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            stderr_text = stderr_buf.getvalue()
            return TaskResult(
                task_id=task_id,
                passed=False,
                failure_step="exception",
                reason=str(exc),
                elapsed_ms=elapsed,
                harness_stderr=stderr_text,
            )

        stderr_text = stderr_buf.getvalue()
        expect_err = check_expect_files(root, task.get("expect_files") or {})
        if expect_err:
            elapsed = (time.perf_counter() - t0) * 1000
            return TaskResult(
                task_id=task_id,
                passed=False,
                failure_step=infer_failure_step(stderr_text, expect_error=expect_err),
                reason=expect_err,
                elapsed_ms=elapsed,
                harness_stderr=stderr_text,
            )

        verify_err = check_task_verify(root, task.get("verify", "none"))
        if verify_err:
            elapsed = (time.perf_counter() - t0) * 1000
            return TaskResult(
                task_id=task_id,
                passed=False,
                failure_step=infer_failure_step(stderr_text, expect_error=verify_err),
                reason=verify_err,
                elapsed_ms=elapsed,
                harness_stderr=stderr_text,
            )

        if "降级 open" in stderr_text and not (answer and "已修复并通过验证" in answer):
            elapsed = (time.perf_counter() - t0) * 1000
            return TaskResult(
                task_id=task_id,
                passed=False,
                failure_step=infer_failure_step(stderr_text),
                reason=f"流水线降级 open；回答：{answer[:200]}",
                elapsed_ms=elapsed,
                harness_stderr=stderr_text,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        return TaskResult(
            task_id=task_id,
            passed=True,
            elapsed_ms=elapsed,
            harness_stderr=stderr_text,
        )


def run_eval(
    tasks: list[dict],
    *,
    fake: bool = True,
    task_filter: str | None = None,
    model_client=None,
    max_new_tokens: int = 512,
) -> list[TaskResult]:
    """执行全部（或筛选后的）任务。"""
    selected = tasks
    if task_filter:
        selected = [t for t in tasks if t.get("id") == task_filter]
        if not selected:
            raise ValueError(f"未找到任务 id={task_filter!r}")

    results: list[TaskResult] = []
    for task in selected:
        results.append(
            run_single_task(
                task,
                fake=fake,
                model_client=model_client,
                max_new_tokens=max_new_tokens,
            ),
        )
    return results


def format_report_markdown(results: list[TaskResult]) -> str:
    """Markdown 报告：task_id、pass/fail、失败步、耗时。"""
    lines = [
        "# Eval 报告",
        "",
        "| 任务 | 结果 | 失败环节 | 原因 | 耗时(ms) |",
        "|------|------|----------|------|----------|",
    ]
    for r in results:
        status = "pass" if r.passed else "fail"
        step = r.failure_step or "—"
        reason = (r.reason or "—").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r.task_id} | {status} | {step} | {reason} | {r.elapsed_ms:.0f} |",
        )
    passed = sum(1 for r in results if r.passed)
    lines.extend(["", f"**合计**：{passed}/{len(results)} 通过"])
    failed = [r for r in results if not r.passed and r.harness_stderr]
    if failed:
        lines.extend(["", "## Harness stderr 摘要（失败任务）", ""])
        for r in failed:
            excerpt = _stderr_excerpt(r.harness_stderr).replace("\n", " ")
            lines.append(f"- **{r.task_id}**（{r.failure_step}）：`{excerpt[:400]}`")
    return "\n".join(lines) + "\n"


def format_report_csv(results: list[TaskResult]) -> str:
    """CSV 报告。"""
    lines = ["task_id,passed,failure_step,reason,elapsed_ms"]
    for r in results:
        reason = (r.reason or "").replace('"', '""')
        lines.append(
            f'{r.task_id},{r.passed},{r.failure_step or ""},"{reason}",{r.elapsed_ms:.0f}',
        )
    return "\n".join(lines) + "\n"


def _build_live_client(args: argparse.Namespace) -> OllamaModelClient:
    return OllamaModelClient(
        model=args.model,
        host=args.host,
        temperature=args.temperature,
        top_p=args.top_p,
        timeout=args.ollama_timeout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="黄金闭环 fix_bug eval")
    parser.add_argument("--fake", action="store_true", help="使用 FakeModel（CI/回归）")
    parser.add_argument("--live", action="store_true", help="使用 Ollama（GL-5 扩展）")
    parser.add_argument("--task", help="仅运行指定 task id")
    parser.add_argument(
        "--tasks",
        type=Path,
        default=DEFAULT_TASKS_PATH,
        help=f"任务清单路径（默认 {DEFAULT_TASKS_PATH}）",
    )
    parser.add_argument(
        "--report",
        choices=("markdown", "csv"),
        default="markdown",
        help="报告格式",
    )
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", dest="top_p", type=float, default=0.9)
    parser.add_argument("--ollama-timeout", dest="ollama_timeout", type=int, default=120)
    parser.add_argument(
        "--max-new-tokens",
        dest="max_new_tokens",
        type=int,
        default=512,
        help="每次 LLM complete 的 num_predict 上限（live 建议 512–1024）",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="跳过 --live 前的 Ollama 连通性检查",
    )
    args = parser.parse_args(argv)

    if not args.fake and not args.live:
        parser.error("须指定 --fake 或 --live")
    if args.fake and args.live:
        parser.error("--fake 与 --live 不可同时使用")

    if args.live and not args.skip_preflight:
        err = check_ollama_available(args.host, args.model)
        if err:
            print(err, file=sys.stderr)
            return 2

    set_wait_display_enabled(False)
    try:
        tasks = load_tasks(args.tasks)
        model_client = _build_live_client(args) if args.live else None
        results = run_eval(
            tasks,
            fake=args.fake,
            task_filter=args.task,
            model_client=model_client,
            max_new_tokens=args.max_new_tokens,
        )
    finally:
        set_wait_display_enabled(True)

    report = (
        format_report_markdown(results)
        if args.report == "markdown"
        else format_report_csv(results)
    )
    print(report, end="")

    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
