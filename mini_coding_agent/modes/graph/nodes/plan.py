"""plan 节点：复用 make_plan，写入 memory.plan。"""

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.platform.util import clip


def run_plan(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    goal = ctx.dag.slots.goal
    locate = ctx.node_outputs.get("locate")
    context = ""
    if locate:
        context = clip("\n".join(locate.data.get("snippets", [])), 500)

    result = agent.run_tool("make_plan", {"goal": goal, "context": context})
    if str(result).startswith("错误："):
        return NodeResult(ok=False, message=result)

    plan = agent.session.get("memory", {}).get("plan")
    return NodeResult(
        ok=True,
        message=result,
        data={"plan": plan},
    )
