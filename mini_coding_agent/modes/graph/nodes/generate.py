"""generate 节点：1× complete → write_file/patch_file（必须经 run_tool / governance）。"""

import re

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult
from mini_coding_agent.platform.protocol import parse
from mini_coding_agent.platform.util import clip
from mini_coding_agent.platform.wait_display import MESSAGE_GENERATE, complete_with_wait_display

_ALLOWED_TOOLS = frozenset({"write_file", "patch_file"})
_NUMBERED_SNIPPET_LINE = re.compile(r"^\s*\d+:\s?(.*)$")


def _snippet_source_lines(ctx: HarnessContext, path_str: str) -> list[str]:
    locate = ctx.node_outputs.get("locate")
    if not locate:
        return []
    normalized = path_str.replace("\\", "/")
    lines: list[str] = []
    for snippet in locate.data.get("snippets", []):
        if normalized not in snippet.replace("\\", "/"):
            continue
        for line in snippet.splitlines():
            match = _NUMBERED_SNIPPET_LINE.match(line)
            if match:
                lines.append(match.group(1))
    return lines


def _patch_old_text_candidates(file_text: str, old_text: str, *, snippet_lines: list[str]) -> list[str]:
    """为 fix_bug 生成有限 old_text 候选（禁止任意文本强行匹配）。"""
    seen = {old_text}
    candidates: list[str] = []

    def add(value: str) -> None:
        if value and value not in seen:
            seen.add(value)
            candidates.append(value)

    add(old_text.rstrip())
    if "\\n" in old_text:
        add(old_text.replace("\\n", "\n"))
    stripped = old_text.strip()
    add(stripped)
    matching_lines = [line for line in file_text.splitlines() if line.strip() == stripped]
    if len(matching_lines) == 1:
        add(matching_lines[0])
    containing_lines = [line for line in file_text.splitlines() if stripped and stripped in line]
    if len(containing_lines) == 1:
        add(containing_lines[0])
    for line in snippet_lines:
        if stripped and (line.strip() == stripped or stripped in line):
            add(line)
    return candidates


def _normalize_patch_args_for_fix_bug(ctx: HarnessContext, name: str, args: dict) -> dict:
    """fix_bug 下在 patch 前对齐 old_text（尾随空白 / 缺缩进 / 唯一子串）。"""
    if name != "patch_file" or ctx.dag.intent_id != "fix_bug":
        return args
    path_str = str(args.get("path", "")).strip()
    old_text = str(args.get("old_text", ""))
    if not path_str or not old_text:
        return args
    try:
        file_path = ctx.agent.path(path_str)
        if not file_path.is_file():
            return args
        file_text = file_path.read_text(encoding="utf-8")
    except Exception:
        return args
    if file_text.count(old_text) == 1:
        return args
    snippet_lines = _snippet_source_lines(ctx, path_str)
    for candidate in _patch_old_text_candidates(file_text, old_text, snippet_lines=snippet_lines):
        if file_text.count(candidate) == 1:
            return {**args, "old_text": candidate}
    return args


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

    if name == "patch_file":
        args = _normalize_patch_args_for_fix_bug(ctx, name, args)

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
        "fix_bug": (
            "偏向修复 traceback/测试失败；patch_file 的 old_text 须与定位上下文源码逐字一致（含缩进）。"
        ),
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
