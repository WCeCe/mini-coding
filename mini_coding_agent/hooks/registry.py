from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

# 符合下面签名的函数，都算 HookHandler 类型
# Callable = “描述函数长什么样”，第一个[]里面是参数，后面是返回类型
HookHandler = Callable[["ToolHookContext"], None]


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
    """Phase 2: 工具边界 Hook 注册表（pre_tool / post_tool）。"""

    def __init__(self):
        # 工具执行前
        self._pre: list[HookHandler] = []
        # 工具执行后
        self._post: list[HookHandler] = []

    # 工具注册
    def register(self, event: str, handler: HookHandler):
        if event == "pre_tool":
            self._pre.append(handler)
        elif event == "post_tool":
            self._post.append(handler)
        else:
            raise ValueError(f"unknown hook event: {event}")

    # 记录时间，并执行回调
    def emit_pre(self, ctx: ToolHookContext):
        ctx._started_at = perf_counter()
        # _dispatch 会按注册顺序执行回调所有的处理器
        self._dispatch(self._pre, ctx)

    def emit_post(self, ctx: ToolHookContext):
        if ctx._started_at:
            ctx.duration_ms = (perf_counter() - ctx._started_at) * 1000
        self._dispatch(self._post, ctx)

    @staticmethod
    # TODO这里抛出异常以后，并没有展示或者log，而是直接跳过，最后再进行优化
    def _dispatch(handlers: list[HookHandler], ctx: ToolHookContext):
        # fail-open：Hook 异常不得拖垮工具主流程
        for handler in handlers:
            try:
                handler(ctx)
            except Exception:
                continue
