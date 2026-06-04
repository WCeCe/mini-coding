"""Locate 用代码片段：read_file 范围、search 解析、统一带行号格式。"""

from __future__ import annotations

import re

from mini_coding_agent.index.query import SymbolHit

# 命中行两侧上下文行数（golden-loop §5 GL-2）
CONTEXT_DELTA = 10
# 单 snippet 最大行数
MAX_SNIPPET_LINES = 120
# files_hint 回退默认读取行数
DEFAULT_FILE_READ_END = 120

_SEARCH_LINE = re.compile(r"^(.+?):(\d+):(.*)$")
_NUMBERED_LINE = re.compile(r"^\s*\d+:", re.MULTILINE)


def snippet_header(file_path: str, start: int, end: int) -> str:
    """统一 snippet 标题：`# file: path L10-L30`。"""
    normalized = file_path.replace("\\", "/")
    return f"# file: {normalized} L{start}-L{end}"


def has_source_lines(snippet: str) -> bool:
    """snippet 是否含 read_file 风格的带行号源码。"""
    return bool(_NUMBERED_LINE.search(snippet))


def read_snippet(agent, rel_path: str, start: int, end: int) -> str:
    """经 run_tool(read_file) 读取并规范为 `# file: … Lx-Ly` + 行号正文。"""
    start = max(1, start)
    end = max(start, end)
    if end - start + 1 > MAX_SNIPPET_LINES:
        end = start + MAX_SNIPPET_LINES - 1

    raw = agent.run_tool("read_file", {"path": rel_path, "start": start, "end": end})
    if str(raw).startswith("错误："):
        return ""

    lines = str(raw).splitlines()
    body_lines = lines[1:] if lines and lines[0].startswith("#") else lines
    header = snippet_header(rel_path, start, end)
    if not body_lines:
        return header
    return header + "\n" + "\n".join(body_lines)


def read_snippet_for_hit(
    agent,
    hit: SymbolHit,
    *,
    delta: int = CONTEXT_DELTA,
) -> str:
    """RIG SymbolHit：按 lineno/end_lineno ±Δ 读取源码片段。"""
    start = max(1, hit.lineno - delta)
    if hit.end_lineno and hit.end_lineno >= hit.lineno:
        end = hit.end_lineno + delta
    else:
        end = hit.lineno + delta
    return read_snippet(agent, hit.file_path, start, end)


def parse_search_hits(search_result: str) -> list[tuple[str, int]]:
    """解析 search/rg 输出 `path:line:content`。"""
    hits: list[tuple[str, int]] = []
    for line in search_result.splitlines():
        text = line.strip()
        if not text or text == "（无匹配）":
            continue
        match = _SEARCH_LINE.match(text)
        if match:
            hits.append((match.group(1).replace("\\", "/"), int(match.group(2))))
    return hits


def merge_line_ranges(line_numbers: list[int], *, delta: int = CONTEXT_DELTA) -> list[tuple[int, int]]:
    """合并相邻命中行为 read_file 区间（每段不超过 MAX_SNIPPET_LINES）。"""
    if not line_numbers:
        return []
    ranges: list[tuple[int, int]] = []
    for lineno in sorted(set(line_numbers)):
        start = max(1, lineno - delta)
        end = lineno + delta
        if ranges and start <= ranges[-1][1] + 1:
            prev_start, prev_end = ranges[-1]
            merged_end = max(prev_end, end)
            if merged_end - prev_start + 1 > MAX_SNIPPET_LINES:
                merged_end = prev_start + MAX_SNIPPET_LINES - 1
            ranges[-1] = (prev_start, merged_end)
        else:
            if end - start + 1 > MAX_SNIPPET_LINES:
                end = start + MAX_SNIPPET_LINES - 1
            ranges.append((start, end))
    return ranges


def snippets_from_search(
    agent,
    search_result: str,
    *,
    symbol: str,
    seen_ranges: set[tuple[str, int, int]],
) -> list[str]:
    """search 命中：每文件按行 ±Δ 读源码，附 `# search:` 说明。"""
    by_file: dict[str, list[int]] = {}
    for file_path, lineno in parse_search_hits(search_result):
        by_file.setdefault(file_path, []).append(lineno)

    result: list[str] = []
    for file_path, line_numbers in by_file.items():
        for start, end in merge_line_ranges(line_numbers):
            key = (file_path, start, end)
            if key in seen_ranges:
                continue
            seen_ranges.add(key)
            body = read_snippet(agent, file_path, start, end)
            if not body:
                continue
            result.append(f"# search: {symbol}\n{body}")
    return result
