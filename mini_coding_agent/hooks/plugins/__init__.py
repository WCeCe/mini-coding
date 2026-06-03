"""内置与自定义 Hook 实现模块；新增观察型 Hook 请放在本目录。

装配入口：`mini_coding_agent.hooks.builtin.register_builtin_hooks`。
基础设施（registry、hook_config）在上级 `hooks/` 目录。
"""

from mini_coding_agent.hooks.plugins.ask_timing_hook import AskTimingHook
from mini_coding_agent.hooks.plugins.shell_audit_hook import ShellAuditHook
from mini_coding_agent.hooks.plugins.trace_display_hook import TraceDisplayHook
from mini_coding_agent.hooks.plugins.trace_hook import ToolTraceHook

__all__ = [
    "AskTimingHook",
    "ShellAuditHook",
    "ToolTraceHook",
    "TraceDisplayHook",
]
