from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

# Hook 回调签名（observe-only；异常由 _dispatch fail-open 吞掉）
AskHookHandler = Callable[["AskHookContext"], None]
LlmHookHandler = Callable[["LlmHookContext"], None]
ToolHookHandler = Callable[["ToolHookContext"], None]
HookHandler = ToolHookHandler


@dataclass
class AskHookContext:
    """单次 ask 的 Hook 上下文；collector 由 AskTimingHook 等在 pre_ask 挂载。"""

    agent: Any
    ask_id: int
    user_message: str
    duration_ms: float = 0.0
    stop_last_llm: bool = False
    collector: Any = None
    _started_at: float = field(default=0.0, repr=False)


@dataclass
class LlmHookContext:
    """主循环单次 LLM iteration 的 Hook 上下文（prompt → complete → parse）。"""

    agent: Any
    ask_ctx: AskHookContext
    attempt: int
    outcome: str = ""
    duration_ms: float = 0.0
    _started_at: float = field(default=0.0, repr=False)


@dataclass
class ToolHookContext:
    """Phase 2: 单次 tool 调用的 Hook 上下文（只读，供观察型回调使用）。"""

    # 一次工具调用的上下文：工具名、args、result、成败、耗时、是否 risky
    agent: Any
    name: str
    args: dict
    tool: dict | None = None
    result: str = ""
    success: bool = False
    duration_ms: float = 0.0
    risky: bool = False
    step: int = 0
    _started_at: float = field(default=0.0, repr=False)


class HookRegistry:
    """Hook 注册表：tool（Phase 2）+ ask / llm（HOOK-ASK-EVENTS）。"""

    def __init__(self):
        self._pre_ask: list[AskHookHandler] = []
        self._post_ask: list[AskHookHandler] = []
        self._pre_llm: list[LlmHookHandler] = []
        self._post_llm: list[LlmHookHandler] = []
        self._pre_tool: list[ToolHookHandler] = []
        self._post_tool: list[ToolHookHandler] = []
        self._active_ask_ctx: AskHookContext | None = None

    def register(self, event: str, handler: Callable[..., None]):
        if event == "pre_ask":
            self._pre_ask.append(handler)
        elif event == "post_ask":
            self._post_ask.append(handler)
        elif event == "pre_llm":
            self._pre_llm.append(handler)
        elif event == "post_llm":
            self._post_llm.append(handler)
        elif event == "pre_tool":
            self._pre_tool.append(handler)
        elif event == "post_tool":
            self._post_tool.append(handler)
        else:
            raise ValueError(f"未知的 hook 事件：{event}")

    def emit_pre_ask(self, ctx: AskHookContext):
        ctx._started_at = perf_counter()
        self._active_ask_ctx = ctx
        self._dispatch(self._pre_ask, ctx)

    def emit_post_ask(self, ctx: AskHookContext):
        if ctx._started_at:
            ctx.duration_ms = (perf_counter() - ctx._started_at) * 1000
        self._dispatch(self._post_ask, ctx)
        self._active_ask_ctx = None

    def emit_pre_llm(self, ctx: LlmHookContext):
        ctx._started_at = perf_counter()
        self._dispatch(self._pre_llm, ctx)

    def emit_post_llm(self, ctx: LlmHookContext):
        if ctx._started_at:
            ctx.duration_ms = (perf_counter() - ctx._started_at) * 1000
        self._dispatch(self._post_llm, ctx)

    def emit_pre(self, ctx: ToolHookContext):
        ctx._started_at = perf_counter()
        self._dispatch(self._pre_tool, ctx)

    def emit_post(self, ctx: ToolHookContext):
        if ctx._started_at:
            ctx.duration_ms = (perf_counter() - ctx._started_at) * 1000
        self._dispatch(self._post_tool, ctx)

    @staticmethod
    def _dispatch(handlers: list[Callable[..., None]], ctx: Any):
        # fail-open：Hook 异常不得拖垮主流程
        for handler in handlers:
            try:
                handler(ctx)
            except Exception:
                continue
