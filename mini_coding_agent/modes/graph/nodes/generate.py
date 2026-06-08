"""generate 节点：1× complete → write_file/patch_file（必须经 run_tool / governance）。"""



import re



from mini_coding_agent.modes.graph.harness_trace import record_stage

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult

from mini_coding_agent.modes.graph.verify_rules import check_fix_bug_must_not_touch_tests

from mini_coding_agent.platform.protocol import parse

from mini_coding_agent.platform.util import clip

from mini_coding_agent.platform.wait_display import MESSAGE_GENERATE, complete_with_wait_display



_ALLOWED_TOOLS = frozenset({"write_file", "patch_file"})

_NUMBERED_SNIPPET_LINE = re.compile(r"^\s*\d+:\s?(.*)$")

_SNIPPET_FILE_HEADER = re.compile(r"^#\s*file:\s*(.+?)\s+L\d+", re.IGNORECASE)

_MAX_FIX_BUG_PATCH_LINES = 120



_INTENT_HINTS = {

    "generate_code": "偏重新增/实现代码或新文件。",

    "fix_bug": (

        "偏向修复 traceback/测试失败。"

        "禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。"

    ),

    "refactor": "偏向结构调整；可参考 memory.plan。",

}



_FIX_BUG_GUIDED_HINT = (

    "系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。"

    "调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。"

)





def run_generate(ctx: HarnessContext) -> NodeResult:

    """调用模型一次，解析 tool 调用，校验后经 governance 写盘。"""

    agent = ctx.agent

    prompt = _build_generate_prompt(ctx)

    raw = complete_with_wait_display(

        agent.model_client,

        prompt,

        agent.max_new_tokens,

        message=MESSAGE_GENERATE,

    )



    tool_call = _parse_tool_call(raw)

    if isinstance(tool_call, NodeResult):

        fallback = _try_guided_codeblock_fallback(ctx, raw)

        if fallback is not None:

            name, args = fallback

        else:

            _record_generate_trace(agent, ctx, prompt, raw, tool_call)

            return tool_call

    else:

        name, args = tool_call



    prep = _prepare_tool_args(ctx, name, args)

    if isinstance(prep, NodeResult):

        _record_generate_trace(agent, ctx, prompt, raw, prep, name=name, args=args)

        return prep

    name, args, path = prep



    result = agent.run_tool(name, args)

    if str(result).startswith("错误："):

        fail = NodeResult(ok=False, message=result)

        _record_generate_trace(agent, ctx, prompt, raw, fail, name=name, args=args, path=path)

        return fail



    ok = NodeResult(

        ok=True,

        message=result,

        data={"tool": name, "args": args, "path": path, "tool_result": result},

    )

    _record_generate_trace(agent, ctx, prompt, raw, ok, name=name, args=args, path=path)

    return ok





def _try_guided_codeblock_fallback(ctx: HarnessContext, raw: str) -> tuple[str, dict] | None:

    """引导模式下模型只返回代码块（无 <tool>）时，提取为 patch_file new_text。"""

    if ctx.dag.intent_id != "fix_bug" or "<tool>" in raw:

        return None

    target = _resolve_fix_bug_patch_target(ctx)

    if not target:

        return None

    path, _ = target

    fence = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)

    code = fence.group(1).strip() if fence else raw.strip()

    if not code or "def " not in code:

        return None

    return "patch_file", {"path": path, "new_text": code}





def _parse_tool_call(raw: str) -> NodeResult | tuple[str, dict]:

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

    return name, args





def _prepare_tool_args(ctx: HarnessContext, name: str, args: dict) -> NodeResult | tuple[str, dict, str]:

    """fix_bug 注入 old_text、写前策略校验；通过则返回 (name, args, path)。"""

    if name == "patch_file":

        injected = _apply_fix_bug_guided_patch(ctx, args)

        if isinstance(injected, NodeResult):

            return injected

        args = injected

        args = _normalize_patch_args_for_fix_bug(ctx, args)



    path = str(args.get("path", "")).strip()

    policy_err = check_fix_bug_must_not_touch_tests(ctx.dag.intent_id, path)

    if policy_err:

        return _policy_block_result(policy_err)

    return name, args, path





def _policy_block_result(message: str) -> NodeResult:

    return NodeResult(

        ok=False,

        message=message,

        data={"method": "lock_tests", "policy_block": True},

    )





def _record_generate_trace(

    agent,

    ctx: HarnessContext,

    prompt: str,

    raw: str,

    result: NodeResult,

    *,

    name: str | None = None,

    args: dict | None = None,

    path: str | None = None,

) -> None:

    output: dict = {"raw": raw, "ok": result.ok, "message": result.message}

    if name:

        output["tool"] = name

    if args is not None:

        output["args"] = dict(args)

    if path:

        output["path"] = path

    record_stage(

        agent,

        "generate",

        input={"prompt": prompt, "attempt": ctx.generate_attempt},

        output=output,

        meta={"intent_id": ctx.dag.intent_id},

    )





def _build_generate_prompt(ctx: HarnessContext) -> str:

    locate = ctx.node_outputs.get("locate")

    snippets = locate.data.get("snippets", []) if locate else []

    context_block = "\n\n".join(snippets) if snippets else "（无定位上下文）"



    intent = ctx.dag.intent_id

    guided_target = _resolve_fix_bug_patch_target(ctx) if intent == "fix_bug" else None

    intent_hint = _INTENT_HINTS.get(intent, "")

    if guided_target:

        intent_hint = f"{intent_hint}{_FIX_BUG_GUIDED_HINT}"

    plan_block = _plan_block(ctx, intent)



    tool_instruction = "根据定位上下文，输出唯一一个 <tool> JSON 调用 write_file 或 patch_file 完成目标。"

    tool_example = (

        '<tool>{"name":"patch_file","args":{"path":"src/foo.py","old_text":"bad","new_text":"good"}}</tool>'

    )

    guided_block = ""

    if guided_target:

        path, old_text = guided_target

        tool_instruction = (

            f"根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，"

            f"path 固定为 {path!r}，仅含 new_text。"

        )

        tool_example = f'<tool>{{"name":"patch_file","args":{{"path":"{path}","new_text":"…完整替换内容…"}}}}</tool>'

        guided_block = f"待替换原文（old_text，系统已确定，勿修改）：\n```\n{old_text}\n```"



    return "\n\n".join(

        part

        for part in (

            "你是 Mini-Coding-Agent 的代码生成节点。",

            f"当前意图：{intent}。{intent_hint}",

            plan_block,

            tool_instruction,

            "不要输出 <final>；不要调用其他工具。",

            f"示例：{tool_example}",

            f"目标：\n{ctx.dag.slots.goal}",

            _retry_block(ctx),

            guided_block,

            "定位上下文：",

            context_block,

        )

        if part

    )





def _retry_block(ctx: HarnessContext) -> str:

    parts: list[str] = []

    if ctx.last_verify_error:

        parts.append(f"上次失败，请修正：\n{ctx.last_verify_error}")

    if ctx.generate_attempt > 0:

        parts.append(f"（第 {ctx.generate_attempt + 1} 次 generate 尝试）")

    return "\n".join(parts)





def _plan_block(ctx: HarnessContext, intent: str) -> str:

    if intent != "refactor":

        return ""

    plan_data = ctx.agent.session.get("memory", {}).get("plan")

    if not plan_data:

        return ""

    return f"任务计划已写入 memory.plan（goal={plan_data.get('goal', '')}）。"





# --- fix_bug：系统注入 old_text（Phase 7.2） ---





def _apply_fix_bug_guided_patch(ctx: HarnessContext, args: dict) -> dict | NodeResult:

    """fix_bug 且能解析目标文件时：系统填 old_text，模型只产 new_text。"""

    if ctx.dag.intent_id != "fix_bug":

        return args



    llm_path = str(args.get("path", "")).strip()

    if llm_path and _is_test_path(llm_path):

        return _policy_block_result(

            f"fix_bug 禁止修改测试文件：{llm_path}；请 patch 定位上下文中的源码文件",

        )



    target = _resolve_fix_bug_patch_target(ctx, llm_path=llm_path)

    if target is None:

        return args



    path, old_text = target

    new_text = args.get("new_text")

    if new_text is None or str(new_text) == "":

        return NodeResult(

            ok=False,

            message="fix_bug patch_file 须包含 new_text（完整替换内容）",

        )



    return {

        "path": path,

        "old_text": old_text,

        "new_text": str(new_text),

    }





def _resolve_fix_bug_patch_target(

    ctx: HarnessContext,

    *,

    llm_path: str = "",

) -> tuple[str, str] | None:

    """从 locate 或 LLM 指定的非 tests 路径读取唯一 old_text。"""

    path = _primary_source_file_from_locate(ctx)

    if not path and llm_path and not _is_test_path(llm_path):

        path = llm_path

    if not path:

        return None



    old_text = _read_patch_old_text(ctx, path)

    if not old_text:

        return None

    try:

        file_text = ctx.agent.path(path).read_text(encoding="utf-8")

    except Exception:

        return None

    if file_text.count(old_text) != 1:

        return None

    return path, old_text





def _primary_source_file_from_locate(ctx: HarnessContext) -> str | None:

    locate = ctx.node_outputs.get("locate")

    if not locate:

        return None



    candidates: list[str] = []

    for raw in locate.data.get("files") or []:

        normalized = str(raw).replace("\\", "/").strip()

        if normalized and not _is_test_path(normalized) and normalized.endswith(".py"):

            candidates.append(normalized)



    if not candidates:

        for snippet in locate.data.get("snippets") or []:

            for line in snippet.splitlines():

                match = _SNIPPET_FILE_HEADER.match(line.strip())

                if match:

                    path = match.group(1).replace("\\", "/").strip()

                    if not _is_test_path(path) and path.endswith(".py"):

                        candidates.append(path)



    seen: set[str] = set()

    for path in candidates:

        if path not in seen:

            seen.add(path)

            return path

    return None





def _read_patch_old_text(ctx: HarnessContext, path_str: str) -> str | None:

    try:

        file_path = ctx.agent.path(path_str)

        if not file_path.is_file():

            return None

        file_text = file_path.read_text(encoding="utf-8")

    except Exception:

        return None



    line_count = len(file_text.splitlines()) or (1 if file_text else 0)

    if line_count <= _MAX_FIX_BUG_PATCH_LINES:

        return file_text



    snippet_text = _snippet_text_for_path(ctx, path_str, file_text)

    return snippet_text





def _snippet_text_for_path(ctx: HarnessContext, path_str: str, file_text: str) -> str | None:

    lines = _snippet_source_lines(ctx, path_str)

    if not lines:

        return None

    for candidate in ("\n".join(lines), "\n".join(lines) + "\n"):

        if candidate and file_text.count(candidate) == 1:

            return candidate

    return None





def _is_test_path(path: str) -> bool:

    normalized = path.replace("\\", "/").strip().lstrip("./")

    return normalized.startswith("tests/") or "/tests/" in normalized





# --- fix_bug：patch old_text 对齐（写盘前兜底） ---





def _normalize_patch_args_for_fix_bug(ctx: HarnessContext, args: dict) -> dict:

    """在 patch 前对齐 old_text（尾随空白 / 缺缩进 / 唯一子串）。"""

    if ctx.dag.intent_id != "fix_bug":

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


