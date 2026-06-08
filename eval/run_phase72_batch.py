#!/usr/bin/env python3
"""批量跑 phase72 剩余 generate 任务（一次性脚本）。"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from eval.run_eval import (  # noqa: E402
    check_ollama_available,
    format_report_json,
    format_report_markdown,
    load_tasks,
    run_eval,
)
from mini_coding_agent.platform.models import OllamaModelClient  # noqa: E402
from mini_coding_agent.platform.wait_display import set_wait_display_enabled  # noqa: E402

TASK_IDS = [
    "syntaxerror_paren",
    "nameerror_greet",
    "missing_return_abs",
    "no_file_hint_add",
    "bench_retry_off_by_one",
    "import_chain_rate",
    "logic_median_even",
]


def main() -> int:
    set_wait_display_enabled(False)
    err = check_ollama_available("http://127.0.0.1:11434", "qwen2.5-coder:7b")
    if err:
        print(err, file=sys.stderr)
        return 2

    tasks = [t for t in load_tasks() if t["id"] in TASK_IDS]
    missing = set(TASK_IDS) - {t["id"] for t in tasks}
    if missing:
        print(f"未找到任务：{sorted(missing)}", file=sys.stderr)
        return 1

    order = {tid: i for i, tid in enumerate(TASK_IDS)}
    tasks.sort(key=lambda t: order[t["id"]])

    client = OllamaModelClient(
        model="qwen2.5-coder:7b",
        host="http://127.0.0.1:11434",
        temperature=0.2,
        top_p=0.9,
        timeout=120,
    )
    results = run_eval(tasks, model_client=client, max_new_tokens=512)

    json_path = _REPO / "eval/runs/live/2026-06-08_phase72-generate-7tasks.json"
    md_path = _REPO / "eval/runs/live/2026-06-08_phase72-generate-7tasks.md"
    json_path.write_text(format_report_json(results), encoding="utf-8")
    md_path.write_text(format_report_markdown(results), encoding="utf-8")

    passed = sum(1 for r in results if r.passed)
    print(f"Done: {passed}/{len(results)} passed")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")
    for r in results:
        status = "pass" if r.passed else "fail"
        ft = r.failure_type or "-"
        print(f"  {r.task_id}: {status} ({ft}) {r.elapsed_ms:.0f}ms")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
