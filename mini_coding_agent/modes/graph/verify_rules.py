"""Harness 与 eval 共用的 verify / lock_tests 规则（EV-1）。"""

from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

from mini_coding_agent.modes.graph.slots import detect_test_command


def normalize_rel_path(path: str) -> str:
    return str(path).replace("\\", "/").strip().lstrip("./")


def is_under_tests(path: str) -> bool:
    rel = normalize_rel_path(path)
    return rel == "tests" or rel.startswith("tests/")


def resolve_test_command(
    workspace_root: Path | str | None,
    slots_command: str | None = None,
) -> str | None:
    """优先 slots，否则按工作区 pytest 迹象探测。"""
    if slots_command:
        return slots_command
    return detect_test_command(workspace_root)


def _is_ignored_test_artifact(rel: str) -> bool:
    """pytest 运行产物（如 __pycache__）不计入 lock_tests 快照。"""
    parts = rel.replace("\\", "/").split("/")
    return "__pycache__" in parts or rel.endswith(".pyc")


def collect_tests_snapshot(root: Path) -> dict[str, str]:
    """采集 tests/ 下全部文件内容快照。"""
    snapshot: dict[str, str] = {}
    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return snapshot
    for path in sorted(tests_dir.rglob("*")):
        if not path.is_file():
            continue
        if ".mini-coding-agent" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if _is_ignored_test_artifact(rel):
            continue
        snapshot[rel] = path.read_text(encoding="utf-8", errors="replace")
    return snapshot


def check_tests_snapshot_unchanged(root: Path, baseline: dict[str, str]) -> str | None:
    """对比 tests/ 快照；baseline 为空则跳过。"""
    if not baseline:
        return None
    current = collect_tests_snapshot(root)
    for rel, expected in baseline.items():
        if rel not in current:
            return f"测试文件被删除或缺失：{rel}"
        if current[rel] != expected:
            return f"测试文件被修改：{rel}"
    for rel in current:
        if rel not in baseline:
            return f"测试目录出现新文件：{rel}"
    return None


def check_generate_did_not_touch_tests(generate_path: str | None) -> str | None:
    if generate_path and is_under_tests(generate_path):
        return f"禁止修改测试文件：{normalize_rel_path(generate_path)}"
    return None


def check_lock_tests_from_setup(root: Path, setup_files: dict) -> str | None:
    """eval 终判：setup_files 中 tests/ 路径内容须保持不变。"""
    for rel_path, expected in setup_files.items():
        rel = normalize_rel_path(str(rel_path))
        if not is_under_tests(rel):
            continue
        full = root / rel
        if not full.is_file():
            return f"测试文件缺失：{rel}"
        actual = full.read_text(encoding="utf-8")
        if actual != expected:
            return f"测试文件被修改：{rel}"
    return None


def workspace_has_tests(root: Path) -> bool:
    return (root / "tests").is_dir()


def run_py_compile_paths(root: Path, paths: list[str]) -> str | None:
    errors: list[str] = []
    for rel in paths:
        full = root / normalize_rel_path(rel)
        if not full.is_file() or full.suffix != ".py":
            continue
        try:
            py_compile.compile(str(full), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{rel}: {exc}")
    if errors:
        return "py_compile 失败：\n" + "\n".join(errors)
    return None


def run_py_compile_all(root: Path) -> str | None:
    errors: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        if ".mini-coding-agent" in py_file.parts:
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{py_file.relative_to(root).as_posix()}: {exc}")
    if errors:
        return "py_compile 失败：\n" + "\n".join(errors)
    return None


def run_pytest(root: Path, *, timeout: int = 60) -> str | None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return f"pytest 失败（exit {proc.returncode}）：{detail[:500]}"
    return None


def run_task_verify(root: Path, verify: str | None) -> str | None:
    """eval 任务级 verify；与 harness 语义对齐。"""
    if verify in ("", "none", None):
        return None
    if verify == "py_compile":
        return run_py_compile_all(root)
    if verify == "pytest":
        return run_pytest(root)
    return f"未知 verify 类型：{verify!r}"
