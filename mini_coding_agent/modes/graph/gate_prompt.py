"""Gate 意图分类专用 prompt（Phase 5.1）。"""

import json


def build_gate_prompt(user_message: str) -> str:
    """拼装单次 complete 用的分类 prompt；要求模型仅返回 JSON。"""
    schema = {
        "intent_id": "generate_code | fix_bug | refactor | explain | project_ops",
        "confidence": "high | low",
        "skill": "null 或 skill 名字符串（可选）",
    }
    return "\n\n".join(
        [
            "你是 Mini-Coding-Agent 的意图分类器（Gate）。",
            "根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。",
            "JSON 字段名必须为英文，说明性文字可用中文。",
            json.dumps(schema, ensure_ascii=False, indent=2),
            _INTENT_DEFINITIONS,
            _BOUNDARY_EXAMPLES,
            "规则：",
            "- confidence=high：意图明确、可归入上述五类之一。",
            "- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。",
            "- skill：若用户明确点名某 Skill 名可填字符串，否则 null。",
            f"用户消息：\n{user_message.strip()}",
        ]
    )


_INTENT_DEFINITIONS = """\
五类意图（intent_id 必须精确使用下列英文 id）：

| intent_id | 含义 | 典型用户话 |
|-----------|------|------------|
| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |
| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |
| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |
| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |
| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |"""

_BOUNDARY_EXAMPLES = """\
边界示例（减少混类）：

1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」
   → 要改文件 → fix_bug（不是 explain）

2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」
   → project_ops（不是 fix_bug）

3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug

4. 「跑一下测试」不改码 → project_ops

5. 意图跨多类且无法确定主目标 → confidence=low"""
