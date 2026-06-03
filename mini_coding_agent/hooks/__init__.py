"""Hook 包：registry / 配置 / 装配 + ``plugins/`` 下的 Hook 实现。

- 基础设施：``registry.py``、``hook_config.py``、``builtin.py``
- Hook 实现：``plugins/``（新增观察型 Hook 请放该目录）
- 配置模板：``hooks.yaml.example``（复制到工作区 ``.mini-coding-agent/hooks.yaml``）
"""

from mini_coding_agent.hooks.builtin import register_builtin_hooks
from mini_coding_agent.hooks.plugins import (
    AskTimingHook,
    ShellAuditHook,
    ToolTraceHook,
    TraceDisplayHook,
)
from mini_coding_agent.hooks.registry import (
    AskHookContext,
    AskHookHandler,
    HookHandler,
    HookRegistry,
    LlmHookContext,
    LlmHookHandler,
    ToolHookContext,
    ToolHookHandler,
)

__all__ = [
    "AskHookContext",
    "AskHookHandler",
    "AskTimingHook",
    "HookHandler",
    "HookRegistry",
    "LlmHookContext",
    "LlmHookHandler",
    "ShellAuditHook",
    "ToolHookContext",
    "ToolHookHandler",
    "ToolTraceHook",
    "TraceDisplayHook",
    "register_builtin_hooks",
]
