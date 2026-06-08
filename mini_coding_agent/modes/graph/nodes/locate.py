"""locate 节点：RIG 图谱优先，再 traceback/search（rg）回退；产出带行号源码 snippet。"""

from pathlib import Path

from mini_coding_agent.modes.graph.snippet import (
    DEFAULT_FILE_READ_END,
    has_source_lines,
    parse_search_hits,
    read_snippet,
    read_snippet_for_hit,
    snippets_from_search,
)
from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.index.query import RigQuery, SymbolHit


def run_locate(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    slots = ctx.dag.slots
    files: list[str] = []
    snippets: list[str] = []
    seen_files: set[str] = set()
    seen_ranges: set[tuple[str, int, int]] = set()
    used_rig = False
    query = RigQuery.for_repo(agent.root)

    for symbol in slots.symbols_hint[:5]:
        if query and _rig_symbol_hits(query, agent, symbol, seen_files, seen_ranges, files, snippets):
            used_rig = True
            continue
        search_result = agent.run_tool("search", {"pattern": symbol, "path": "."})
        if search_result and "（无匹配）" not in search_result:
            snippets.extend(
                snippets_from_search(
                    agent,
                    search_result,
                    symbol=symbol,
                    seen_ranges=seen_ranges,
                ),
            )
            for file_path, _lineno in parse_search_hits(search_result):
                rel = _resolve_existing_file(agent.root, file_path) or file_path
                _track_file(rel, seen_files, files)

    for hint in slots.files_hint:
        if query:
            used_rig = _rig_file_hits(query, agent, hint, seen_files, seen_ranges, files, snippets) or used_rig
        rel = _resolve_existing_file(agent.root, hint)
        if rel:
            _add_file(agent, rel, seen_files, seen_ranges, files, snippets)

    if not files and slots.files_hint:
        files = list(dict.fromkeys(slots.files_hint))

    _ensure_source_snippet(agent, slots, seen_files, seen_ranges, files, snippets)

    min_required = ctx.locate_min_snippets_with_source_lines
    snippet_count = sum(1 for s in snippets if has_source_lines(s))
    if min_required > 0 and snippet_count < min_required:
        return NodeResult(
            ok=False,
            message="locate：无有效源码 snippet",
            data={
                "files": files,
                "snippets": snippets,
                "symbols_hint": list(slots.symbols_hint),
                "used_rig": used_rig,
            },
        )

    source = "rig+回退" if used_rig else "hint+search"
    return NodeResult(
        ok=True,
        message=f"定位完成（{source}）：{len(files)} 个文件",
        data={
            "files": files,
            "snippets": snippets,
            "symbols_hint": list(slots.symbols_hint),
            "used_rig": used_rig,
        },
    )


def _track_file(rel: str, seen_files: set[str], files: list[str]) -> None:
    if rel not in seen_files:
        seen_files.add(rel)
        files.append(rel)


def _append_snippet(
    snippets: list[str],
    seen_ranges: set[tuple[str, int, int]],
    file_path: str,
    body: str,
    *,
    prefix: str = "",
) -> None:
    if not body or not has_source_lines(body):
        return
    # 从 header 解析范围键，避免重复片段
    first_line = body.splitlines()[0] if body else ""
    key = _range_key_from_header(file_path, first_line)
    if key and key in seen_ranges:
        return
    if key:
        seen_ranges.add(key)
    text = f"{prefix}\n{body}" if prefix else body
    snippets.append(text)


def _range_key_from_header(file_path: str, header_line: str) -> tuple[str, int, int] | None:
    """解析 `# file: path L10-L30`。"""
    normalized = file_path.replace("\\", "/")
    marker = f"# file: {normalized} L"
    if marker not in header_line:
        return None
    try:
        range_part = header_line.split(marker, 1)[1]
        start_s, end_s = range_part.split("-L", 1)
        return (normalized, int(start_s), int(end_s))
    except (ValueError, IndexError):
        return None


def _rig_symbol_hits(
    query: RigQuery,
    agent,
    symbol: str,
    seen_files: set[str],
    seen_ranges: set[tuple[str, int, int]],
    files: list[str],
    snippets: list[str],
) -> bool:
    hits = query.by_symbol(symbol)
    if not hits:
        return False
    for hit in hits:
        _track_file(hit.file_path, seen_files, files)
        body = read_snippet_for_hit(agent, hit)
        prefix = f"# rig: {hit.qualname} ({hit.kind}) @ {hit.file_path}:{hit.lineno}"
        _append_snippet(snippets, seen_ranges, hit.file_path, body, prefix=prefix)
    return True


def _rig_file_hits(
    query: RigQuery,
    agent,
    hint: str,
    seen_files: set[str],
    seen_ranges: set[tuple[str, int, int]],
    files: list[str],
    snippets: list[str],
) -> bool:
    normalized = hint.replace("\\", "/").lstrip("./")
    found = False
    for hit in query.by_file(normalized):
        found = True
        _append_rig_hit(agent, hit, seen_files, seen_ranges, files, snippets)
    for neighbor in query.one_hop_neighbors(normalized):
        found = True
        _track_file(neighbor, seen_files, files)
        body = read_snippet(agent, neighbor, 1, DEFAULT_FILE_READ_END)
        prefix = f"# rig: neighbor {neighbor}"
        _append_snippet(snippets, seen_ranges, neighbor, body, prefix=prefix)
    return found


def _append_rig_hit(
    agent,
    hit: SymbolHit,
    seen_files: set[str],
    seen_ranges: set[tuple[str, int, int]],
    files: list[str],
    snippets: list[str],
) -> None:
    _track_file(hit.file_path, seen_files, files)
    body = read_snippet_for_hit(agent, hit)
    prefix = f"# rig: {hit.qualname} @ {hit.file_path}:{hit.lineno}"
    _append_snippet(snippets, seen_ranges, hit.file_path, body, prefix=prefix)


def _add_file(
    agent,
    rel: str,
    seen_files: set[str],
    seen_ranges: set[tuple[str, int, int]],
    files: list[str],
    snippets: list[str],
    *,
    end_line: int = DEFAULT_FILE_READ_END,
) -> None:
    if rel in seen_files:
        return
    if not _resolve_existing_file(agent.root, rel):
        return
    _track_file(rel, seen_files, files)
    body = read_snippet(agent, rel, 1, end_line)
    _append_snippet(snippets, seen_ranges, rel, body)


def _ensure_source_snippet(
    agent,
    slots,
    seen_files: set[str],
    seen_ranges: set[tuple[str, int, int]],
    files: list[str],
    snippets: list[str],
) -> None:
    """无带行号源码时，对 files_hint 中首个存在的 .py 读 1–120 行。"""
    if any(has_source_lines(s) for s in snippets):
        return
    for hint in slots.files_hint:
        rel = _resolve_existing_file(agent.root, hint)
        if rel and rel.endswith(".py"):
            _add_file(agent, rel, seen_files, seen_ranges, files, snippets)
            return
    for rel in files:
        if rel.endswith(".py") and _resolve_existing_file(agent.root, rel):
            _add_file(agent, rel, seen_files, seen_ranges, files, snippets)
            return


def _resolve_existing_file(root: Path, hint: str) -> str | None:
    candidate = Path(hint.replace("\\", "/").lstrip("./"))
    path = candidate if candidate.is_absolute() else root / candidate
    if path.is_file():
        try:
            return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
        except ValueError:
            return hint
    return None
