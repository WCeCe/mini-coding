"""explain 节点：只读说明；禁止 write_file / patch_file / run_shell。"""

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.platform.protocol import parse
from mini_coding_agent.platform.util import clip
from mini_coding_agent.platform.wait_display import MESSAGE_EXPLAIN, complete_with_wait_display

_FORBIDDEN_TOOLS = frozenset({"write_file", "patch_file", "run_shell"})


def run_explain(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    prompt = _build_explain_prompt(ctx)
    raw = complete_with_wait_display(
        agent.model_client,
        prompt,
        agent.max_new_tokens,
        message=MESSAGE_EXPLAIN,
    )
    kind, payload = parse(raw)
    if kind == "final":
        final = str(payload).strip()
    else:
        final = str(raw).strip()
    if not final:
        return NodeResult(ok=False, message="explain 返回为空")
    return NodeResult(ok=True, message=final, data={"final": final})


def _build_explain_prompt(ctx: HarnessContext) -> str:
    locate = ctx.node_outputs.get("locate")
    snippets = locate.data.get("snippets", []) if locate else []
    context_block = "\n\n".join(snippets) if snippets else "（无定位上下文）"
    return "\n\n".join(
        [
            "你是 Mini-Coding-Agent 的代码解释节点（只读）。",
            "根据定位上下文解释代码如何工作；不要建议改文件；不要调用任何工具。",
            "仅输出 <final>...</final> 中文说明。",
            f"用户问题：\n{ctx.dag.slots.goal}",
            "定位上下文：",
            clip(context_block, 2000),
        ]
    )


def assert_no_risky_tools(tool_name: str) -> None:
    """供测试断言 explain 路径未调用 risky 工具。"""
    if tool_name in _FORBIDDEN_TOOLS:
        raise AssertionError(f"explain 禁止调用 {tool_name}")
