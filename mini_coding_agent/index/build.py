"""RIG 离线建图：遍历 Python 文件，ast 解析符号与 import 边。"""

import ast
from pathlib import Path

from mini_coding_agent.platform.constants import IGNORED_PATH_NAMES
from mini_coding_agent.index.store import RigStore, default_db_path, rig_db_exists


def build_rig(repo_root: str | Path, *, db_path: Path | None = None) -> dict:
    """全量重建图谱；返回统计信息。"""
    root = Path(repo_root).resolve()
    store = RigStore(db_path or default_db_path(root))
    store.init_schema()
    store.clear()

    file_count = 0
    symbol_count = 0
    import_count = 0

    for py_path in _iter_python_files(root):
        rel = str(py_path.relative_to(root)).replace("\\", "/")
        mtime = py_path.stat().st_mtime
        store.upsert_file(rel, mtime)
        file_count += 1
        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError:
            continue
        visitor = _AstIndexer(rel, store)
        visitor.visit(tree)
        symbol_count += visitor.symbol_count
        import_count += visitor.import_count

    return {
        "db_path": str(store.db_path),
        "files": file_count,
        "symbols": symbol_count,
        "imports": import_count,
    }


def ensure_rig(repo_root: str | Path) -> dict:
    """Harness 前置条件：工作区尚无 rig.db 时全量构建。"""
    root = Path(repo_root).resolve()
    db_path = default_db_path(root)
    if rig_db_exists(root):
        return {
            "built": False,
            "db_path": str(db_path),
            "files": 0,
            "symbols": 0,
            "imports": 0,
        }
    stats = build_rig(root)
    stats["built"] = True
    return stats


def _iter_python_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_PATH_NAMES for part in rel_parts):
            continue
        yield path


class _AstIndexer(ast.NodeVisitor):
    def __init__(self, file_path: str, store: RigStore):
        self.file_path = file_path
        self.store = store
        self.class_stack: list[str] = []
        self.symbol_count = 0
        self.import_count = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualname = ".".join([*self.class_stack, node.name])
        self._add_symbol(node.name, "class", node.lineno, node.end_lineno, qualname)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        qualname = ".".join([*self.class_stack, node.name]) if self.class_stack else node.name
        kind = "method" if self.class_stack else "function"
        self._add_symbol(node.name, kind, node.lineno, node.end_lineno, qualname)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.store.add_import(self.file_path, alias.name, name, node.lineno)
            self.import_count += 1

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                imported = "*"
            else:
                imported = alias.asname or alias.name
            self.store.add_import(self.file_path, module, imported, node.lineno)
            self.import_count += 1

    def _add_symbol(self, name: str, kind: str, lineno: int, end_lineno: int | None, qualname: str) -> None:
        self.store.add_symbol(self.file_path, name, kind, lineno, end_lineno, qualname)
        self.symbol_count += 1
