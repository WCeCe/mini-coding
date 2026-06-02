"""Phase 2.1: 终端实时 trace 展示 Hook。"""

import sys

from mini_coding_agent.hooks.registry import HookRegistry, ToolHookContext


class TraceDisplayHook:
    """每步 tool 完成后向 stderr 打印一行摘要（与模型 final 输出区分）。"""

    def __init__(self, registry: HookRegistry):
        registry.register("post_tool", self.post_tool)

    def post_tool(self, ctx: ToolHookContext):
        status = "成功" if ctx.success else "失败"
        line = f"[mini-agent] #{ctx.step} {ctx.name} {status} {ctx.duration_ms:.1f}ms"
        print(line, file=sys.stderr)
