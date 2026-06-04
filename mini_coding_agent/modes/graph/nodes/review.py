"""review 节点：1× complete，对照意图与变更摘要。"""

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.platform.protocol import parse
from mini_coding_agent.platform.util import clip
from mini_coding_agent.platform.wait_display import MESSAGE_REVIEW, complete_with_wait_display


def run_review(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    prompt = _build_review_prompt(ctx)
    raw = complete_with_wait_display(
        agent.model_client,
        prompt,
        agent.max_new_tokens,
        message=MESSAGE_REVIEW,
    )
    kind, payload = parse(raw)
    if kind == "final":
        final = str(payload).strip()
    else:
        final = str(raw).strip()
    if not final:
        return NodeResult(ok=False, message="review 返回为空")
    return NodeResult(ok=True, message=final, data={"final": final})


def _build_review_prompt(ctx: HarnessContext) -> str:
    generate = ctx.node_outputs.get("generate")
    ops = ctx.node_outputs.get("ops")
    verify = ctx.node_outputs.get("verify")
    if generate:
        change_summary = generate.message
    elif ops:
        change_summary = ops.message
    else:
        change_summary = "（无变更）"
    verify_summary = verify.message if verify else "（未验证）"
    return "\n\n".join(
        [
            "你是 Mini-Coding-Agent 的审查节点。",
            f"用户目标：{ctx.dag.slots.goal}",
            f"意图：{ctx.dag.intent_id}",
            "变更摘要：",
            clip(change_summary, 800),
            "验证结果：",
            clip(verify_summary, 400),
            "请用中文给出简短审查结论，输出 <final>...</final>。",
        ]
    )
