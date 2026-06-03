"""run_tool 管道：validate → repeated → Hook → plan-first / governance / approve → run。"""

from mini_coding_agent.governance import run_governed_file_tool
from mini_coding_agent.hooks import ToolHookContext
from mini_coding_agent.tools.validators import repeated_tool_call, tool_example, validate_tool
from mini_coding_agent.util import clip, tool_result_success


# 运行工具
def run_tool(agent, name, args):
    agent._last_tool_meta = {}
    # 从build好的tools中找到对应的
    tool = agent.tools.get(name)
    if tool is None:
        return f"错误：未知工具 '{name}'"
    try:
        # 校验工具是否可用
        validate_tool(agent, name, args)
    except Exception as exc:
        example = tool_example(name)
        message = f"错误：{name} 参数无效：{exc}"
        if example:
            message += f"\n示例：{example}"
        return message
    # 校验是否连续使用工具，谨防死循环
    if repeated_tool_call(agent.session["history"], name, args):
        return invoke_tool_with_hooks(
            agent,
            name,
            args,
            tool,
            lambda: (
                f"错误：连续两次相同调用 {name}；请换用其他工具或返回 <final>"
            ),
        )
    # Phase 2: 校验通过后，经 Hook 包裹实际执行（含治理流程）
    return invoke_tool_with_hooks(
        agent,
        name,
        args,
        tool,
        lambda: execute_tool_after_validation(agent, name, args, tool),
    )


def invoke_tool_with_hooks(agent, name, args, tool, execute):
    """Phase 2: 每次 run_tool 至多一对 pre_tool / post_tool。"""
    args = args or {}
    ctx = ToolHookContext(
        agent=agent,
        name=name,
        args=args,
        tool=tool,
        risky=bool(tool.get("risky")),
    )
    agent.hook_registry.emit_pre(ctx)
    result = execute()
    ctx.result = str(result)
    ctx.success = tool_result_success(result)
    agent.hook_registry.emit_post(ctx)
    return result


def execute_tool_after_validation(agent, name, args, tool):
    # Phase 3: --plan-first 门控（在 validate 之后、approve/治理之前；仅拦截 write/patch/shell）
    # 返回 error 字符串给主循环，不进入 governance.run_governed_file_tool / approve
    if agent.plan_first and tool.get("risky") and not agent._ask_plan_satisfied:
        return (
            "错误：已启用 --plan-first，请先在本轮 ask 内成功调用 make_plan，"
            f"再使用 risky 工具 '{name}'（write_file、patch_file、run_shell）"
        )
    # write_file / patch_file 治理主流程见 mini_coding_agent.governance.run_governed_file_tool
    if name in {"write_file", "patch_file"}:
        return run_governed_file_tool(agent, name, args)
    # 是否允许使用有风险的工具
    if tool["risky"] and not agent.approve(name, args):
        return f"错误：{name} 审批被拒绝"
    try:
        # 在 build_tools() 里，每个工具都注册了 "run"，指向一个 Python 方法，"run": self.tool_read_file
        # tool["run"](args)等价于self.tool_read_file(args)
        # clip是指对得到的文本超过4k就进行截断
        return clip(tool["run"](args))
    except Exception as exc:
        return f"错误：工具 {name} 执行失败：{exc}"
