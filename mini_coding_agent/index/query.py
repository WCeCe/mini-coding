"""RIG 查询：按符号名、文件路径；可选 1-hop 邻居。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mini_coding_agent.index.store import RigStore, default_db_path


@dataclass
class SymbolHit:
    file_path: str
    name: str
    kind: str
    lineno: int
    qualname: str
    end_lineno: int | None = None


@dataclass
class ImportHit:
    file_path: str
    module: str
    imported_name: str | None
    lineno: int | None = None


class RigQuery:
    def __init__(self, db_path: Path):
        self.store = RigStore(db_path)

    @classmethod
    def for_repo(cls, repo_root: Path) -> RigQuery | None:
        path = default_db_path(repo_root)
        if not path.is_file():
            return None
        return cls(path)

    def by_symbol(self, name: str, *, limit: int = 20) -> list[SymbolHit]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT file_path, name, kind, lineno, end_lineno, qualname
                FROM symbols
                WHERE name = ?
                ORDER BY file_path, lineno
                LIMIT ?
                """,
                (name, limit),
            ).fetchall()
        return [_row_to_symbol(row) for row in rows]

    def by_file(self, path: str, *, limit: int = 50) -> list[SymbolHit]:
        normalized = path.replace("\\", "/").lstrip("./")
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT file_path, name, kind, lineno, end_lineno, qualname
                FROM symbols
                WHERE file_path = ? OR file_path LIKE ?
                ORDER BY lineno
                LIMIT ?
                """,
                (normalized, f"%{normalized}", limit),
            ).fetchall()
        return [_row_to_symbol(row) for row in rows]

    def imports_for_file(self, path: str, *, limit: int = 30) -> list[ImportHit]:
        normalized = path.replace("\\", "/").lstrip("./")
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT file_path, module, imported_name, lineno
                FROM imports
                WHERE file_path = ?
                ORDER BY lineno
                LIMIT ?
                """,
                (normalized, limit),
            ).fetchall()
        return [
            ImportHit(
                file_path=row["file_path"],
                module=row["module"],
                imported_name=row["imported_name"],
                lineno=row["lineno"],
            )
            for row in rows
        ]

    def one_hop_neighbors(self, file_path: str, *, limit: int = 20) -> list[str]:
        """1-hop：同文件 import 目标模块所在文件 + 导入本文件模块名的其他文件。"""
        normalized = file_path.replace("\\", "/").lstrip("./")
        neighbors: list[str] = []
        seen: set[str] = {normalized}

        module_prefix = normalized.replace("/", ".").removesuffix(".py")
        with self.store.connect() as conn:
            for row in conn.execute(
                "SELECT DISTINCT module FROM imports WHERE file_path = ?",
                (normalized,),
            ).fetchall():
                module = row["module"] or ""
                if not module:
                    continue
                pattern = module.replace(".", "/") + "%"
                for hit in conn.execute(
                    """
                    SELECT DISTINCT path FROM files
                    WHERE path LIKE ? AND path != ?
                    LIMIT ?
                    """,
                    (pattern + ".py", normalized, limit),
                ).fetchall():
                    path = hit["path"]
                    if path not in seen:
                        seen.add(path)
                        neighbors.append(path)

            if module_prefix:
                for hit in conn.execute(
                    """
                    SELECT DISTINCT file_path FROM imports
                    WHERE module = ? OR module LIKE ?
                    LIMIT ?
                    """,
                    (module_prefix, module_prefix + ".%", limit),
                ).fetchall():
                    path = hit["file_path"]
                    if path not in seen:
                        seen.add(path)
                        neighbors.append(path)

        return neighbors[:limit]


def _row_to_symbol(row) -> SymbolHit:
    return SymbolHit(
        file_path=row["file_path"],
        name=row["name"],
        kind=row["kind"],
        lineno=row["lineno"],
        end_lineno=row["end_lineno"],
        qualname=row["qualname"],
    )
