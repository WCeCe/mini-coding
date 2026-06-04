"""verify 节点：pytest 或 py_compile。"""

import py_compile

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult


def run_verify(ctx: HarnessContext) -> NodeResult:
    slots = ctx.dag.slots
    if slots.test_command:
        return _run_test_command(ctx, slots.test_command)
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
