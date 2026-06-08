"""verify 节点：pytest（含 tests/ 时）或 py_compile。"""

import py_compile
from pathlib import Path

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.modes.graph.verify_rules import (
    check_generate_did_not_touch_tests,
    check_tests_snapshot_unchanged,
    resolve_test_command,
)


def run_verify(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    root = Path(agent.root)

    generate = ctx.node_outputs.get("generate")
    gen_path = generate.data.get("path") if generate else None
    lock_err = check_generate_did_not_touch_tests(gen_path)
    if lock_err:
        return NodeResult(ok=False, message=lock_err, data={"method": "lock_tests"})

    lock_err = check_tests_snapshot_unchanged(root, ctx.test_baseline)
    if lock_err:
        return NodeResult(ok=False, message=lock_err, data={"method": "lock_tests"})

    test_command = resolve_test_command(root, ctx.dag.slots.test_command)
    if test_command:
        return _run_test_command(ctx, test_command)

    return _run_py_compile(ctx)


def _run_test_command(ctx: HarnessContext, command: str) -> NodeResult:
    agent = ctx.agent
    result = agent.run_tool("run_shell", {"command": command, "timeout": 60})
    ok = result.startswith("exit_code: 0")
    return NodeResult(
        ok=ok,
        message=result,
        data={"method": "shell", "command": command},
    )


def _run_py_compile(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    paths = _modified_python_paths(ctx)
    if not paths:
        return NodeResult(ok=False, message="verify：未找到可编译的 Python 文件")

    errors: list[str] = []
    for rel in paths:
        full = agent.root / rel
        if not full.is_file() or full.suffix != ".py":
            continue
        try:
            py_compile.compile(str(full), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{rel}: {exc}")

    if errors:
        return NodeResult(
            ok=False,
            message="py_compile 失败：\n" + "\n".join(errors),
            data={"method": "py_compile", "paths": paths},
        )
    return NodeResult(
        ok=True,
        message=f"py_compile 通过：{', '.join(paths)}",
        data={"method": "py_compile", "paths": paths},
    )


def _modified_python_paths(ctx: HarnessContext) -> list[str]:
    generate = ctx.node_outputs.get("generate")
    if not generate:
        return []
    path = generate.data.get("path")
    if path and str(path).endswith(".py"):
        return [str(path).replace("\\", "/")]
    locate = ctx.node_outputs.get("locate")
    if locate:
        return [p for p in locate.data.get("files", []) if str(p).endswith(".py")]
    return []
