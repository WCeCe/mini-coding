"""Verify 失败输出压缩为 Generate retry 可读摘要。"""

import re

from mini_coding_agent.platform.util import clip

_MAX_CHARS = 800
_MAX_LINES = 8

# traceback / pytest 末尾常见异常行
_EXCEPTION_LINE_RE = re.compile(
    r"^(\w+(?:Error|Exception|Failed))(?:\s*:\s*(.*))?$",
)
_FILE_LINE_RE = re.compile(r'^\s*File "([^"]+)", line (\d+)')
_PY_COMPILE_HEADER = "py_compile 失败："


def format_error_for_model(raw: str) -> str:
    """将 verify 长输出压缩为 3–8 行关键信息（≤800 字符）。"""
    text = str(raw).strip()
    if not text:
        return ""

    if text.startswith(_PY_COMPILE_HEADER):
        summary = _format_py_compile(text)
    elif "Traceback" in text or _has_exception_line(text):
        summary = _format_traceback(text)
    else:
        summary = _format_generic(text)

    return _finalize(summary, text)


def _has_exception_line(text: str) -> bool:
    for line in text.splitlines():
        if _EXCEPTION_LINE_RE.match(line.strip()):
            return True
    return False


def _finalize(summary: str, fallback: str) -> str:
    """截断至行数/字符上限；空摘要则 clip 原文。"""
    if not summary.strip():
        return clip(fallback, _MAX_CHARS)
    lines = summary.splitlines()
    if len(lines) > _MAX_LINES:
        lines = lines[-_MAX_LINES:]
    result = "\n".join(lines)
    if len(result) > _MAX_CHARS:
        return clip(result, _MAX_CHARS)
    return result


def _format_py_compile(text: str) -> str:
    body = text[len(_PY_COMPILE_HEADER) :].strip()
    blocks = body.split("\n\n") if "\n\n" in body else [body]
    lines_out: list[str] = []

    for block in blocks:
        block_lines = block.strip().splitlines()
        if not block_lines:
            continue

        header = block_lines[0]
        rel = header.split(":", 1)[0].strip() if ":" in header else ""
        file_match = _FILE_LINE_RE.search(header) or _FILE_LINE_RE.search(block)
        lineno = file_match.group(2) if file_match else "?"
        path = rel or (file_match.group(1) if file_match else "?")

        exc_line = ""
        context: list[str] = []
        for ln in block_lines[1:]:
            stripped = ln.strip()
            if _EXCEPTION_LINE_RE.match(stripped):
                exc_line = stripped
            elif stripped.startswith(("^", "~")) or (
                exc_line and not stripped.startswith("File")
            ):
                context.append(ln.rstrip())

        if not exc_line:
            for ln in reversed(block_lines):
                stripped = ln.strip()
                if stripped and not stripped.startswith("File") and ":" in stripped:
                    exc_line = stripped
                    break

        if exc_line:
            lines_out.append(f"{path}:{lineno} {exc_line}")
        else:
            lines_out.append(f"{path}:{lineno}")
        lines_out.extend(context[:3])
        if len(lines_out) >= _MAX_LINES:
            break

    return "\n".join(lines_out[:_MAX_LINES])


def _format_traceback(text: str) -> str:
    body = text
    if "stderr:" in text:
        idx = text.rfind("stderr:")
        stderr_body = text[idx + len("stderr:") :].strip()
        if stderr_body and stderr_body != "（空）":
            body = stderr_body
        elif "stdout:" in text:
            idx = text.rfind("stdout:")
            stdout_body = text[idx + len("stdout:") :].split("stderr:")[0].strip()
            if stdout_body and stdout_body != "（空）":
                body = stdout_body

    all_lines = body.splitlines()
    exc_idx = None
    for i in range(len(all_lines) - 1, -1, -1):
        if _EXCEPTION_LINE_RE.match(all_lines[i].strip()):
            exc_idx = i
            break

    if exc_idx is None:
        return _format_generic(body)

    selected: list[str] = [all_lines[exc_idx].strip()]
    for i in range(exc_idx - 1, -1, -1):
        ln = all_lines[i]
        stripped = ln.strip()
        if not stripped:
            continue
        if _FILE_LINE_RE.match(ln) or stripped.startswith("^"):
            selected.insert(0, stripped)
        elif stripped.startswith("Traceback"):
            break
        elif len(selected) >= _MAX_LINES - 1:
            break
        elif exc_idx - i <= 4:
            selected.insert(0, stripped)

    return "\n".join(selected[:_MAX_LINES])


def _format_generic(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) > _MAX_LINES:
        lines = lines[-_MAX_LINES:]
    return "\n".join(lines)
