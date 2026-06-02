"""Phase 2.1: 内置 Hook YAML 配置加载与 CLI 覆盖。"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# 默认 shell 审计模式（可被 hooks.yaml 覆盖）
DEFAULT_SHELL_WARN_PATTERNS = [
    r"rm -rf",
    r"curl.*\|.*sh",
]


@dataclass
class HookConfig:
    """内置 Hook 启停与 shell 审计参数。"""

    session_trace: bool = True
    trace_display: bool = True
    shell_audit: bool = True
    shell_warn_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_SHELL_WARN_PATTERNS))
    config_path: Path | None = None


def default_hook_config() -> HookConfig:
    return HookConfig()


def load_hook_config(path: Path) -> tuple[HookConfig, list[str]]:
    """读取 hooks.yaml；缺失或错误时 fail-open 回退默认。"""
    warnings: list[str] = []
    if not path.is_file():
        return default_hook_config(), warnings

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"hooks.yaml 无法读取（{path}）：{exc}；使用默认配置")
        return default_hook_config(), warnings

    if raw is None:
        return default_hook_config(), warnings
    if not isinstance(raw, dict):
        warnings.append("hooks.yaml 根节点必须是映射；使用默认配置")
        return default_hook_config(), warnings

    config = default_hook_config()
    config.config_path = path

    builtin = raw.get("builtin_hooks", {})
    if builtin is None:
        builtin = {}
    elif not isinstance(builtin, dict):
        warnings.append("builtin_hooks 必须是映射；忽略该节")
        builtin = {}

    for yaml_key, attr in (
        ("session_trace", "session_trace"),
        ("trace_display", "trace_display"),
        ("shell_audit", "shell_audit"),
    ):
        value = builtin.get(yaml_key)
        if value is None:
            continue
        if not isinstance(value, bool):
            warnings.append(f"builtin_hooks.{yaml_key} 必须是布尔值；使用默认值")
            continue
        setattr(config, attr, value)

    shell_section = raw.get("shell_audit")
    if shell_section is None:
        return config, warnings
    if not isinstance(shell_section, dict):
        warnings.append("shell_audit 必须是映射；忽略该节")
        return config, warnings

    patterns = shell_section.get("warn_patterns")
    if patterns is None:
        return config, warnings
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        warnings.append("shell_audit.warn_patterns 必须是字符串列表；使用默认模式")
        return config, warnings

    config.shell_warn_patterns = patterns
    return config, warnings


def apply_cli_overrides(config: HookConfig, args) -> HookConfig:
    """CLI 显式旗标覆盖 YAML（仅当用户传入对应 flag 时生效）。"""
    if getattr(args, "no_trace_display", False):
        config.trace_display = False
    if getattr(args, "no_session_trace", False):
        config.session_trace = False
    if getattr(args, "no_shell_audit", False):
        config.shell_audit = False
    return config


def emit_config_warnings(warnings: list[str]) -> None:
    for message in warnings:
        print(f"[mini-agent] hooks 配置：{message}", file=sys.stderr)
