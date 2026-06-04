"""按 HookConfig 装配内置 Hook 栈。"""

from mini_coding_agent.platform.hooks.plugins.ask_timing_hook import AskTimingHook
from mini_coding_agent.platform.hooks.hook_config import HookConfig
from mini_coding_agent.platform.hooks.registry import HookRegistry
from mini_coding_agent.platform.hooks.plugins.shell_audit_hook import ShellAuditHook
from mini_coding_agent.platform.hooks.plugins.trace_display_hook import TraceDisplayHook
from mini_coding_agent.platform.hooks.plugins.trace_hook import ToolTraceHook


def register_builtin_hooks(registry: HookRegistry, config: HookConfig) -> None:
    """内置 Hook 唯一注册入口：trace 栈 + ask timing jsonl（各可独立启停）。"""
    if config.session_trace:
        ToolTraceHook(registry)
    if config.trace_display:
        TraceDisplayHook(registry)
    if config.shell_audit:
        ShellAuditHook(registry, config.shell_warn_patterns)
    if config.ask_timing:
        AskTimingHook(registry)
