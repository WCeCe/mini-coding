"""ops 节点：白名单 run_shell；禁止写文件。"""

from mini_coding_agent.modes.graph.types import DEFAULT_OPS_ALLOWLIST, HarnessContext, NodeResult

# 白名单前缀（与 DEFAULT_OPS_ALLOWLIST / slots.ops_allowlist 一致）
OPS_ALLOWLIST_PREFIXES = DEFAULT_OPS_ALLOWLIST


def run_ops(ctx: HarnessContext) -> NodeResult:
    allowlist = list(ctx.dag.slots.ops_allowlist or DEFAULT_OPS_ALLOWLIST)
    command = infer_ops_command(ctx.dag.slots.goal)
    if not command:
        return NodeResult(ok=False, message="ops：无法从目标推断 shell 命令")

    if not command_is_allowlisted(command, allowlist):
        return NodeResult(
            ok=False,
            message=f"ops：命令不在白名单：{command}",
        )

    result = ctx.agent.run_tool("run_shell", {"command": command, "timeout": 60})
    ok = str(result).startswith("exit_code: 0")
    return NodeResult(
        ok=ok,
        message=result,
        data={"command": command},
    )


def command_is_allowlisted(command: str, allowlist: list[str]) -> bool:
    cmd = command.strip()
    for entry in allowlist:
        prefix = entry.strip()
        if cmd == prefix or cmd.startswith(prefix + " "):
            return True
    return False


def infer_ops_command(goal: str) -> str | None:
    """从用户目标推断 ops 命令（规则，无 LLM）。"""
    text = goal.lower()
    if "git status" in text:
        return "git status"
    if "git diff" in text:
        return "git diff"
    if "git log" in text:
        return "git log"
    if "pip install" in text:
        return "pip install"
    if "pip list" in text:
        return "pip list"
    if "pytest" in text or "跑测试" in goal or "跑 pytest" in goal:
        return "python -m pytest -q"
    return None
