"""内置 AskTimingHook：post_llm / post_tool 收集事件，post_ask 写 jsonl。"""

import json
from pathlib import Path
from time import perf_counter

from mini_coding_agent.hooks.registry import (
    AskHookContext,
    HookRegistry,
    LlmHookContext,
    ToolHookContext,
)
from mini_coding_agent.util import clip, now

ASK_LOG_USER_MESSAGE_LIMIT = 300


class AskTimingCollector:
    """单次 ask 的内存事件收集器；生命周期绑在 AskHookContext.collector。"""

    def __init__(self, session_id: str, ask_id: int, user_message: str):
        self.session_id = session_id
        self.ask_id = ask_id
        self.user_message = clip(user_message.strip(), ASK_LOG_USER_MESSAGE_LIMIT)
        self.events: list[dict] = []
        self._started_at = perf_counter()

    def record_llm(self, attempt: int, duration_ms: float, outcome: str) -> None:
        self.events.append(
            {
                "kind": "llm",
                "attempt": attempt,
                "duration_ms": round(duration_ms, 2),
                "outcome": outcome,
            }
        )

    def record_tool(self, step: int, name: str, duration_ms: float, success: bool) -> None:
        self.events.append(
            {
                "kind": "tool",
                "step": step,
                "name": name,
                "duration_ms": round(duration_ms, 2),
                "success": success,
            }
        )

    def mark_last_llm_stop(self) -> None:
        """步数/attempt 上限退出时，将最近一条 llm 的 outcome 标为 stop。"""
        for event in reversed(self.events):
            if event["kind"] == "llm":
                event["outcome"] = "stop"
                return

    def build_record(self) -> dict:
        total_ms = round((perf_counter() - self._started_at) * 1000, 2)
        return {
            "session_id": self.session_id,
            "ask_id": self.ask_id,
            "user_message": self.user_message,
            "total_ms": total_ms,
            "events": self.events,
            "created_at": now(),
        }


def append_ask_timing_log(repo_root: Path, record: dict) -> None:
    """Append 一行 JSON 到 <repo>/.mini-coding-agent/logs/<session_id>.jsonl；fail-open。"""
    try:
        log_dir = Path(repo_root) / ".mini-coding-agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"{record['session_id']}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


class AskTimingHook:
    """订阅 ask/llm/tool 边界，写入 OPT-ASK-TIMING 口径的 session jsonl。"""

    def __init__(self, registry: HookRegistry):
        registry.register("pre_ask", self.pre_ask)
        registry.register("post_llm", self.post_llm)
        registry.register("pre_tool", self.pre_tool)
        registry.register("post_tool", self.post_tool)
        registry.register("post_ask", self.post_ask)

    def pre_ask(self, ctx: AskHookContext) -> None:
        ctx.collector = AskTimingCollector(
            ctx.agent.session["id"],
            ctx.ask_id,
            ctx.user_message,
        )

    def post_llm(self, ctx: LlmHookContext) -> None:
        collector = ctx.ask_ctx.collector
        if collector is None:
            return
        collector.record_llm(ctx.attempt, ctx.duration_ms, ctx.outcome)

    def pre_tool(self, ctx: ToolHookContext) -> None:
        ask_ctx = ctx.agent.hook_registry._active_ask_ctx
        collector = ask_ctx.collector if ask_ctx else None
        if collector is None:
            return
        # session_trace 关闭时 ToolTraceHook 未分配 step，自行计数以对齐步序
        if not ctx.step:
            tool_count = sum(1 for event in collector.events if event["kind"] == "tool")
            ctx.step = tool_count + 1

    def post_tool(self, ctx: ToolHookContext) -> None:
        ask_ctx = ctx.agent.hook_registry._active_ask_ctx
        collector = ask_ctx.collector if ask_ctx else None
        if collector is None:
            return
        collector.record_tool(
            step=ctx.step,
            name=ctx.name,
            duration_ms=ctx.duration_ms,
            success=ctx.success,
        )

    def post_ask(self, ctx: AskHookContext) -> None:
        collector = ctx.collector
        if collector is None:
            return
        if ctx.stop_last_llm:
            collector.mark_last_llm_stop()
        append_ask_timing_log(ctx.agent.root, collector.build_record())
