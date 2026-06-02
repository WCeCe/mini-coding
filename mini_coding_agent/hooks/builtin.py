"""按 HookConfig 装配内置 Hook 栈。"""

from mini_coding_agent.hooks.hook_config import HookConfig
from mini_coding_agent.hooks.registry import HookRegistry
from mini_coding_agent.hooks.shell_audit_hook import ShellAuditHook
from mini_coding_agent.hooks.trace_display_hook import TraceDisplayHook
from mini_coding_agent.hooks.trace_hook import ToolTraceHook


def register_builtin_hooks(registry: HookRegistry, config: HookConfig) -> None:
    """三层栈：session trace + 终端展示 + shell 审计（各可独立启停）。"""
    if config.session_trace:
        ToolTraceHook(registry)
    if config.trace_display:
        TraceDisplayHook(registry)
    if config.shell_audit:
        ShellAuditHook(registry, config.shell_warn_patterns)
