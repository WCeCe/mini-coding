"""verify 节点：与 eval 终判共用 run_workspace_verify。"""

from pathlib import Path

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.modes.graph.verify_rules import (
    check_generate_did_not_touch_tests,
    check_tests_snapshot_unchanged,
    lock_tests_enabled,
    resolve_test_command,
    run_workspace_verify,
    workspace_has_tests,
)


def run_verify(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    root = Path(agent.root)

    if lock_tests_enabled():
        generate = ctx.node_outputs.get("generate")
        gen_path = generate.data.get("path") if generate else None
        lock_err = check_generate_did_not_touch_tests(gen_path)
        if lock_err:
            return NodeResult(ok=False, message=lock_err, data={"method": "lock_tests"})

        lock_err = check_tests_snapshot_unchanged(root, ctx.test_baseline)
        if lock_err:
            return NodeResult(ok=False, message=lock_err, data={"method": "lock_tests"})

    slots_cmd = getattr(ctx.dag.slots, "test_command", None) if ctx.dag.slots else None
    err = run_workspace_verify(root, slots_test_command=slots_cmd)
    method = _verify_method(root, slots_cmd)

    if err:
        return NodeResult(ok=False, message=err, data={"method": method})

    return NodeResult(
        ok=True,
        message=f"verify 通过（{method}）",
        data={"method": method},
    )


def _verify_method(root: Path, slots_cmd: str | None) -> str:
    if workspace_has_tests(root) or resolve_test_command(root, slots_cmd):
        return "pytest"
    return "py_compile"


def _modified_python_paths(ctx: HarnessContext) -> list[str]:
    """供 executor session 记录；保留兼容导入。"""
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
