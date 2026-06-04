"""Phase 2.1: run_shell 危险命令审计 Hook（只观察，不阻断）。"""

import re
import sys

from mini_coding_agent.platform.hooks.registry import HookRegistry, ToolHookContext
from mini_coding_agent.platform.util import middle, now


class ShellAuditHook:
    """post_tool 检查 run_shell 命令；命中模式时 stderr 告警并写入 session。"""

    def __init__(self, registry: HookRegistry, warn_patterns: list[str]):
        # 预编译正则，避免每步重复 compile
        self._patterns: list[tuple[str, re.Pattern[str]]] = []
        for pattern in warn_patterns:
            try:
                self._patterns.append((pattern, re.compile(pattern, re.IGNORECASE)))
            except re.error:
                # 无效正则 fail-open：跳过该条，不拖垮 Agent
                continue
        registry.register("post_tool", self.post_tool)

    def post_tool(self, ctx: ToolHookContext):
        if ctx.name != "run_shell":
            return
        command = str((ctx.args or {}).get("command", ""))
        if not command:
            return

        for pattern_str, compiled in self._patterns:
            if not compiled.search(command):
                continue
            preview = middle(command, 80)
            print(
                f"[mini-agent] shell 审计：匹配模式 '{pattern_str}' — 命令：{preview}",
                file=sys.stderr,
            )
            entry = {
                "step": ctx.step,
                "pattern": pattern_str,
                "command_preview": preview,
                "success": ctx.success,
                "created_at": now(),
            }
            ctx.agent.session.setdefault("shell_audit", []).append(entry)
