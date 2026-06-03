"""Prompt 形状：build_prefix、memory_text、history_text、prompt 组装。"""

import json

from mini_coding_agent.constants import MAX_HISTORY
from mini_coding_agent.planning import plan_summary_text
from mini_coding_agent.skills import loaded_skills_summary
from mini_coding_agent.util import clip


# 构建prompt的prefix部分，同一次Agent生命周期内 基本不变
def build_prefix(tools, skill_catalog, workspace):
    tool_lines = []
    for name, tool in tools.items():
        # 获取工具的参数path、start啥的
        fields = ", ".join(f"{key}: {value}" for key, value in tool["schema"].items())
        # 获取风险
        risk = "需审批" if tool["risky"] else "安全"
        # 写成这样的形式：tool_lines.append("- read_file(path: str, start: int=1, end: int=200) [safe] Read a UTF-8 file by line range.")
        tool_lines.append(f"- {name}({fields}) [{risk}] {tool['description']}")
    # 1.工具列表
    tool_text = "\n".join(tool_lines)
    # 2，这是模型该怎么输出的例子
    examples = "\n".join(
        [
            '<tool>{"name":"list_files","args":{"path":"."}}</tool>',
            '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":80}}</tool>',
            '<tool name="write_file" path="binary_search.py"><content>def binary_search(nums, target):\n    return -1\n</content></tool>',
            '<tool name="patch_file" path="binary_search.py"><old_text>return -1</old_text><new_text>return mid</new_text></tool>',
            '<tool>{"name":"run_shell","args":{"command":"uv run --with pytest python -m pytest -q","timeout":20}}</tool>',
            '<tool>{"name":"make_plan","args":{"goal":"add tests for module X","context":"read README first"}}</tool>',
            '<tool>{"name":"load_skill","args":{"name":"code-review"}}</tool>',
            "<final>Done.</final>",
        ]
    )
    # 3.规则
    rules = "\n".join([
        "- 不要猜测工作区内容，请使用工具获取事实。",
        "- 每次只返回一个 <tool>...</tool> 或一个 <final>...</final>。",
        "- tool 调用格式示例：",
        '  <tool>{"name":"tool_name","args":{...}}</tool>',
        "- write_file、patch_file 的多行内容优先使用 XML 格式：",
        '  <tool name="write_file" path="file.py"><content>...</content></tool>',
        "- 最终回答格式：",
        "  <final>你的回答</final>",
        "- 不要编造工具执行结果。",
        "- 回答简洁、具体。",
        "- 用户要求创建或更新明确路径的文件时，用 write_file 或 patch_file，不要反复 list_files。",
        "- 为现有代码写测试前，先 read_file 阅读实现。",
        "- 写测试时匹配当前实现，除非用户明确要求改代码。",
        "- 新建文件应完整可运行，包含必要 import。",
        "- 同一参数重复调用无效工具时，换工具或返回 <final>。",
        "- 必填工具参数不能为空。不得用空 args 调用 read_file、write_file、patch_file、run_shell、delegate、make_plan、load_skill。",
        "- 多文件改动、需求含糊或用户要求规划时：先用 read_file/search 调查，再 make_plan，再执行 risky 工具（write_file、patch_file、run_shell）。",
        "- delegate = 有界只读子 Agent 调查；make_plan = 单次结构化任务拆分（不能替代 delegate）。",
    ])
    # Phase 4: 阶段一 Skill metadata 清单（不含 SKILL.md 正文）
    skills_text = skill_catalog.metadata_block()
    # 构建prompt的prefix部分，prefix又分为五个部分：
    # 1.You are Mini-Coding-Agent...
    # 2. 规则：Rules: + rules
    # 3. 工具列表：Tools: + tool_lines
    # 4. 案例：Valid response examples: + examples
    # 5. 仓库快照：workspace.text()（仓库快照）
    return "\n\n".join([
        "你是 Mini-Coding-Agent，通过 Ollama 运行的本地小型编程 Agent。",
        "规则：\n" + rules,
        "工具：\n" + tool_text,
        "有效响应示例：\n" + examples,
        skills_text,
        workspace.text(),
    ])


# 构建memory（含 Phase 3 plan 摘要，会进入 prompt() 供模型对照执行）
def memory_text(memory):
    notes = "\n".join(f"- {note}" for note in memory["notes"]) or "- 无"
    plan = memory.get("plan")
    if plan:
        plan_lines = plan_summary_text(plan).splitlines()
        plan_block = "\n".join(f"  {line}" for line in plan_lines)
    else:
        plan_block = "  - 无"
    # Phase 4: 已加载 Skill 摘要 + 正文（进入后续 prompt）
    loaded = memory.get("loaded_skills") or {}
    loaded_lines = [loaded_skills_summary(loaded)]
    for skill_name in sorted(loaded.keys()):
        item = loaded[skill_name]
        if isinstance(item, dict) and item.get("body"):
            body = str(item["body"]).strip()
            loaded_lines.append(f"  [{skill_name} 正文]\n{body}")
    loaded_block = "\n".join(loaded_lines)
    return "\n".join([
        "记忆：",
        f"- task: {memory['task'] or '-'}",
        f"- files: {', '.join(memory['files']) or '-'}",
        "- plan:",
        plan_block,
        "- loaded_skills:",
        loaded_block,
        "- notes:",
        notes,
    ])


#####################################################
#### 4) Context Reduction And Output Management #####
#####################################################
# 获取历史信息
def history_text(history):
    if not history:
        return "- （空）"
    # 存储格式化后的历史文本行，用于最终拼接输出
    lines = []
    # 只针对非最近（较旧）的 read_file 工具调用
    # 例如：历史中出现了三次对 /etc/config 的旧读取记录，最终只输出第一条。这样可以避免历史文本中出现大量重复的读取内容，节省空间。
    seen_reads = set()
    recent_start = max(0, len(history) - 6)
    for index, item in enumerate(history):
        # recent是bool变量，来区分旧和新
        recent = index >= recent_start
        if item["role"] == "tool" and item["name"] in ("write_file", "patch_file"):
            path = str(item["args"].get("path", ""))
            # 移除path
            seen_reads.discard(path)
        # 是工具、且是都文档、并且不是最近的
        if item["role"] == "tool" and item["name"] == "read_file" and not recent:
            path = str(item["args"].get("path", ""))
            # 添加到set集合里面
            if path in seen_reads:
                continue
            seen_reads.add(path)
        # [tool:write_file] {"content": "Hello", "path": "/tmp/test.txt"}
        # content
        if item["role"] == "tool":
            limit = 900 if recent else 180
            lines.append(f"[tool:{item['name']}] {json.dumps(item['args'], sort_keys=True)}")
            lines.append(clip(item["content"], limit))
        else:
            # 存的是user原话、retry的“model returned malformed tool JSON”重试说明、还有final的回答、次数用尽等
            limit = 900 if recent else 220
            lines.append(f"[{item['role']}] {clip(item['content'], limit)}")

    return clip("\n".join(lines), MAX_HISTORY)


########################################################
#### 2) Prompt Shape And Cache Reuse (Continued) #######
########################################################
# prompt分为四个部分：
# 1.前缀，一般一个Agent不会变动
# 2.记忆部分包含task、files（文档路径）、notes（干了哪些东西）三部分
# 3.历史记忆（经过压缩、去重、截断后拼成文本）
# 4.用户要求
def build_prompt(prefix, memory, history, user_message):
    return "\n\n".join([
        prefix,
        memory_text(memory),
        "对话记录：\n" + history_text(history),
        "当前用户请求：\n" + user_message,
    ])
