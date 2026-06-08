import difflib
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from mini_coding_agent.platform.constants import MAX_TOOL_OUTPUT

#一些基本的工具
def now():
    return datetime.now(timezone.utc).isoformat()


# Supporting helper for component 4 (context reduction and output management).
def clip(text, limit=MAX_TOOL_OUTPUT):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[已截断 {len(text) - limit} 字符]"


def middle(text, limit):
    text = str(text).replace("\n", " ")
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    left = (limit - 3) // 2
    right = limit - 3 - left
    return text[:left] + "..." + text[-right:]


# 把任意文本内容转换成一个固定长度的 SHA-256 哈希值
def text_sha256(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


# 一个文本文件的 SHA-256 哈希值
def file_sha256(path):
    if not path.is_file():
        return None
    return text_sha256(path.read_text(encoding="utf-8"))


def ensure_trailing_newline(content) -> str:
    """POSIX 文本文件习惯：非空内容以换行结尾（Phase 7.4）。"""
    text = str(content)
    if text and not text.endswith("\n"):
        return text + "\n"
    return text


# 保证原子性，先临时再原子替换
def atomic_write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = ensure_trailing_newline(content)
    # 创建一个临时文件，后缀为.mini-agent.tmp，with_suffix替换路径中的文件后缀名
    tmp = path.with_suffix(path.suffix + ".mini-agent.tmp")
    tmp.write_text(normalized, encoding="utf-8")
    tmp.replace(path)


# 构建unified diff，并返回渲染后的字符串
def build_unified_diff(rel_path, before, after):
    # 按行对比
    before_lines = str(before).splitlines(keepends=True)
    after_lines = str(after).splitlines(keepends=True)
    # 都为空，则返回(no changes)
    if not before_lines and not after_lines:
        return "（无变更）"
    # diff格式
    diff_lines = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        lineterm="",
    )
    # 渲染成字符串
    rendered = "\n".join(diff_lines)
    # 如果有变化，则返回渲染后的字符串
    if rendered:
        return rendered
    # 没有变化，则返回(no changes)
    if before_lines == after_lines:
        return "（无变更）"
    return f"--- a/{rel_path}\n+++ b/{rel_path}\n（文件已变更）"


# 用于审计，存入sessions里面，有40行的限制，但是审批的时候是完整的diff
def diff_summary(diff_text, max_lines=40):
    # 按行分割
    lines = str(diff_text).splitlines()
    # 如果行数小于等于40，则返回diff_text
    if len(lines) <= max_lines:
        return diff_text
    # 超过40行，则截断，返回前40行，后面加上... (omitted more lines)
    omitted = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n...（另有 {omitted} 行未显示）"


def tool_result_success(result):
    """Phase 2: 判断 tool 返回字符串是否表示成功（供 Hook 使用）。"""
    text = str(result)
    return not text.startswith("error:") and not text.startswith("错误：")
