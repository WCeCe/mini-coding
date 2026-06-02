"""Hook 实现目录：注册表 + 内置 Hook；后续新增 Hook 请放在本包内。

配置模板：同目录 ``hooks.yaml.example``（复制到工作区 ``.mini-coding-agent/hooks.yaml`` 后生效）。
运行时默认读取工作区路径，不会自动加载包内的 .example 文件。
"""

from mini_coding_agent.hooks.builtin import register_builtin_hooks
from mini_coding_agent.hooks.registry import HookHandler, HookRegistry, ToolHookContext
from mini_coding_agent.hooks.shell_audit_hook import ShellAuditHook
from mini_coding_agent.hooks.trace_display_hook import TraceDisplayHook
from mini_coding_agent.hooks.trace_hook import ToolTraceHook

__all__ = [
    "HookHandler",
    "HookRegistry",
    "ShellAuditHook",
    "ToolHookContext",
    "ToolTraceHook",
    "TraceDisplayHook",
    "register_builtin_hooks",
]
