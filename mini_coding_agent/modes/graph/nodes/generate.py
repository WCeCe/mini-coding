"""generate 节点：1× complete → write_file/patch_file（必须经 run_tool / governance）。"""

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.platform.protocol import parse
from mini_coding_agent.platform.util import clip
from mini_coding_agent.platform.wait_display import MESSAGE_GENERATE, complete_with_wait_display

_ALLOWED_TOOLS = frozenset({"write_file", "patch_file"})


def run_generate(ctx: HarnessContext) -> NodeResult:
    agent = ctx.agent
    prompt = _build_generate_prompt(ctx)
    raw = complete_with_wait_display(
        agent.model_client,
        prompt,
        agent.max_new_tokens,
        message=MESSAGE_GENERATE,
    )
    kind, payload = parse(raw)
    if kind != "tool":
        return NodeResult(ok=False, message=f"generate 须返回 tool 调用，收到：{clip(raw, 200)}")

    name = str(payload.get("name", "")).strip()
    args = payload.get("args") or {}
    if name not in _ALLOWED_TOOLS:
        return NodeResult(
            ok=False,
            message=f"generate 仅允许 write_file/patch_file，收到：{name}",
        )

    result = agent.run_tool(name, args)
    if str(result).startswith("错误："):
        return NodeResult(ok=False, message=result)

    path = str(args.get("path", "")).strip()
    return NodeResult(
        ok=True,
        message=result,
        data={"tool": name, "args": args, "path": path, "tool_result": result},
    )


def _build_generate_prompt(ctx: HarnessContext) -> str:
    locate = ctx.node_outputs.get("locate")
    snippets = locate.data.get("snippets", []) if locate else []
    context_block = "\n\n".join(snippets) if snippets else "（无定位上下文）"
    retry_block = ""
    if ctx.last_verify_error:
        retry_block = f"\n上次验证失败，请修正：\n{ctx.last_verify_error}\n"
    if ctx.generate_attempt > 0:
        retry_block += f"\n（第 {ctx.generate_attempt + 1} 次 generate 尝试）\n"

    intent = ctx.dag.intent_id
    goal = ctx.dag.slots.goal
    intent_hint = {
        "generate_code": "偏重新增/实现代码或新文件。",
        "fix_bug": "偏向修复 traceback/测试失败。",
        "refactor": "偏向结构调整；可参考 memory.plan。",
    }.get(intent, "")
    plan_block = ""
    plan_data = ctx.agent.session.get("memory", {}).get("plan")
    if intent == "refactor" and plan_data:
        plan_block = f"\n任务计划已写入 memory.plan（goal={plan_data.get('goal', '')}）。\n"
    return "\n\n".join(
        [
            "你是 Mini-Coding-Agent 的代码生成节点。",
            f"当前意图：{intent}。{intent_hint}",
            plan_block.strip(),
            "根据定位上下文，输出唯一一个 <tool> JSON 调用 write_file 或 patch_file 完成目标。",
            "不要输出 <final>；不要调用其他工具。",
            '示例：<tool>{"name":"patch_file","args":{"path":"src/foo.py","old_text":"bad","new_text":"good"}}</tool>',
            f"目标：\n{goal}",
            retry_block.strip(),
            "定位上下文：",
            context_block,
        ]
    )
