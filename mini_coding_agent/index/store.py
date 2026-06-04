"""RIG SQLite 存储（stdlib）。"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    mtime REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    lineno INTEGER NOT NULL,
    end_lineno INTEGER,
    qualname TEXT NOT NULL,
    FOREIGN KEY (file_path) REFERENCES files(path)
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_path);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    module TEXT NOT NULL,
    imported_name TEXT,
    lineno INTEGER,
    FOREIGN KEY (file_path) REFERENCES files(path)
);

CREATE INDEX IF NOT EXISTS idx_imports_file ON imports(file_path);
CREATE INDEX IF NOT EXISTS idx_imports_module ON imports(module);
"""


def default_db_path(repo_root: Path) -> Path:
    return Path(repo_root) / ".mini-coding-agent" / "rig.db"


def rig_db_exists(repo_root: Path) -> bool:
    return default_db_path(repo_root).is_file()


class RigStore:
    """RIG 图谱读写；全量 build 时先清空再写入。"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def clear(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM imports")
            conn.execute("DELETE FROM symbols")
            conn.execute("DELETE FROM files")
            conn.commit()

    def upsert_file(self, path: str, mtime: float) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO files (path, mtime) VALUES (?, ?)",
                (path, mtime),
            )
            conn.commit()

    def add_symbol(
        self,
        file_path: str,
        name: str,
        kind: str,
        lineno: int,
        end_lineno: int | None,
        qualname: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO symbols (file_path, name, kind, lineno, end_lineno, qualname)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_path, name, kind, lineno, end_lineno, qualname),
            )
            conn.commit()

    def add_import(
        self,
        file_path: str,
        module: str,
        imported_name: str | None,
        lineno: int | None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO imports (file_path, module, imported_name, lineno)
                VALUES (?, ?, ?, ?)
                """,
                (file_path, module, imported_name, lineno),
            )
            conn.commit()
