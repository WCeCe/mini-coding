"""Planner 槽位规则填充（Phase 5.2）：无 LLM，从用户消息与 traceback 提取。"""

import re
from pathlib import Path

from mini_coding_agent.modes.graph.types import DEFAULT_OPS_ALLOWLIST, GOAL_MAX_LEN
from mini_coding_agent.platform.util import clip

# Python traceback: File "path", line N
_TRACEBACK_FILE = re.compile(r'File "([^"]+)", line \d+', re.MULTILINE)
# 用户消息中的相对路径
_MESSAGE_PATH = re.compile(
    r"(?<![\w./-])([\w./\\-]+\.(?:py|json|md|yaml|yml|toml|txt|ini|cfg))(?![\w./-])",
    re.IGNORECASE,
)
# 常见异常中的符号名
_SYMBOL_PATTERNS = (
    re.compile(r"NameError: name '([^']+)'"),
    re.compile(r"AttributeError: .* '([^']+)'"),
    re.compile(r"ImportError: .* '([^']+)'"),
    re.compile(r"ModuleNotFoundError: No module named '([^']+)'"),
    re.compile(r"in (\w+)\s*$", re.MULTILINE),
)


def fill_slots(
    user_message: str,
    *,
    intent_id: str,
    skill_name: str | None = None,
    workspace_root: str | Path | None = None,
) -> dict:
    """规则填充槽位；返回 DagSlots 构造参数字典。"""
    goal = clip(user_message.strip(), GOAL_MAX_LEN)
    files_hint = extract_files_hint(user_message, workspace_root)
    symbols_hint = extract_symbols_hint(user_message)
    slots: dict = {
        "goal": goal,
        "files_hint": files_hint,
        "symbols_hint": symbols_hint,
    }
    test_command = detect_test_command(workspace_root)
    if test_command:
        slots["test_command"] = test_command
    if skill_name:
        slots["skill_name"] = skill_name
    if intent_id == "project_ops":
        slots["ops_allowlist"] = list(DEFAULT_OPS_ALLOWLIST)
    return slots


def extract_files_hint(user_message: str, workspace_root: str | Path | None = None) -> list[str]:
    """从 traceback 与用户消息中提取文件路径 hint（去重保序）。"""
    seen: set[str] = set()
    result: list[str] = []
    root = Path(workspace_root).resolve() if workspace_root else None

    for match in _TRACEBACK_FILE.finditer(user_message):
        _append_unique(result, seen, _normalize_path(match.group(1), root))

    for match in _MESSAGE_PATH.finditer(user_message):
        _append_unique(result, seen, _normalize_path(match.group(1), root))

    return result


def extract_symbols_hint(user_message: str) -> list[str]:
    """从 traceback / 异常信息提取符号 hint。"""
    seen: set[str] = set()
    result: list[str] = []
    for pattern in _SYMBOL_PATTERNS:
        for match in pattern.finditer(user_message):
            symbol = match.group(1).strip()
            if symbol and not symbol.startswith("<"):
                _append_unique(result, seen, symbol)
    return result


def detect_test_command(workspace_root: str | Path | None) -> str | None:
    """工作区存在 pytest 迹象时返回默认测试命令。"""
    if workspace_root is None:
        return None
    root = Path(workspace_root)
    if not root.is_dir():
        return None
    if (root / "pytest.ini").exists():
        return "python -m pytest -q"
    if (root / "tests").is_dir():
        return "python -m pytest -q"
    pyproject = root / "pyproject.toml"
    if pyproject.is_file() and "pytest" in pyproject.read_text(encoding="utf-8", errors="replace"):
        return "python -m pytest -q"
    return None


def _normalize_path(raw: str, workspace_root: Path | None) -> str:
    path = raw.replace("\\", "/").strip()
    if workspace_root is None:
        return path
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return str(candidate.resolve().relative_to(workspace_root.resolve())).replace("\\", "/")
        except ValueError:
            return path
    return path.lstrip("./")


def _append_unique(bucket: list[str], seen: set[str], item: str) -> None:
    if not item or item in seen:
        return
    seen.add(item)
    bucket.append(item)
