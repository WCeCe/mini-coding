from mini_coding_agent.platform.hooks.registry import HookRegistry, ToolHookContext
from mini_coding_agent.platform.util import now


class ToolTraceHook:
    """Phase 2: 内置 trace Hook，将工具步序、耗时、成败写入 session。"""

    def __init__(self, registry: HookRegistry):
        registry.register("pre_tool", self.pre_tool)
        registry.register("post_tool", self.post_tool)

    # 执行前记录
    def pre_tool(self, ctx: ToolHookContext):
        trace = ctx.agent.session.setdefault("tool_trace", [])
        ctx.step = len(trace) + 1

    # 执行后记录
    def post_tool(self, ctx: ToolHookContext):
        entry = {
            "step": ctx.step,
            "name": ctx.name,
            "success": ctx.success,
            "duration_ms": round(ctx.duration_ms, 2),
            "risky": ctx.risky,
            "created_at": now(),
        }
        ctx.agent.session.setdefault("tool_trace", []).append(entry)
        # risky 工具写 audit 条目（不替代 approve 审批）
        if ctx.risky:
            audit_entry = {
                **entry,
                "args_keys": sorted(ctx.args.keys()),
            }
            ctx.agent.session.setdefault("tool_audit", []).append(audit_entry)
