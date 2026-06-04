"""Phase 3：make_plan 的结构化规划辅助模块。

职责：
- 拼装 planning 专用 prompt（与主 Agent 的 ask 循环分离）
- 从模型输出中抽取并校验 plan JSON
- 生成工具返回值与 memory 用的 plan 摘要

数据流（由 agent.tool_make_plan 调用）：
  goal/context + workspace 快照 → build_planning_prompt → model complete
  → parse_plan_response → validate_plan → memory.plan + format_plan_tool_result

注意：本模块不发起 tool 循环；与 delegate（子 Agent 多步调查）无关。
"""

import json
import re

# 任务级步骤上限（struct §3 建议 ≤12；超出则 validate_plan 拒绝）
PLAN_MAX_STEPS = 12


def build_planning_prompt(goal, context, workspace_snapshot):
    """拼装 planning 专用 prompt；要求模型只返回一个 JSON 对象（任务级步骤，非函数级清单）。"""
    context_block = ""
    if context and str(context).strip():
        context_block = f"\nAgent 提供的补充上下文：\n{context.strip()}\n"
    return "\n\n".join([
        "你是 Mini-Coding-Agent 的任务规划助手。",
        "将用户目标拆分为任务级步骤，每步须有清晰的验收标准（acceptance）。",
        "不要列出函数级实现细节或具体代码修改清单。",
        "仅回复一个 JSON 对象（不要用 markdown 代码围栏，不要附加说明文字）。",
        "JSON 字段名必须为英文（如下所示），字段值请使用中文（除非专有名词）：",
        json.dumps(
            {
                "goal": "字符串：与用户目标相同或精炼后的表述",
                "steps": [
                    {
                        "id": "1",
                        "title": "步骤标题（任务级）",
                        "acceptance": "如何验收本步已完成",
                        "risky_hint": "可选：可能涉及 write_file / patch_file / run_shell",
                    }
                ],
                "assumptions": ["假设条件，字符串数组"],
                "out_of_scope": ["明确不做的事项，字符串数组"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        f"约束：最多 {PLAN_MAX_STEPS} 步；每步必须包含 id、title、acceptance。",
        workspace_snapshot,
        f"待规划目标：\n{goal.strip()}",
        context_block,
    ])


def extract_json_object(raw):
    """从模型输出中提取 JSON 对象（容忍 markdown ```json 围栏与前后说明文字）。"""
    text = str(raw).strip()
    if not text:
        raise ValueError("规划模型返回为空")
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("规划响应中未找到 JSON 对象")
    return text[start : end + 1]


def parse_plan_response(raw):
    """解析并校验 plan JSON；失败时抛出 ValueError（由 tool_make_plan 转为工具 error 字符串）。"""
    try:
        data = json.loads(extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 无效：{exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("plan 必须是 JSON 对象")
    validate_plan(data)
    return data


def validate_plan(plan):
    """就地规范化并校验 plan 字段（goal、steps id/title/acceptance、assumptions、out_of_scope）与步数上限。"""
    goal = str(plan.get("goal", "")).strip()
    if not goal:
        raise ValueError("字段 goal 不能为空")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("字段 steps 必须为非空数组")
    if len(steps) > PLAN_MAX_STEPS:
        raise ValueError(f"步骤过多（最多 {PLAN_MAX_STEPS} 步）")
    seen_ids = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"第 {index} 步必须是对象")
        step_id = str(step.get("id", "")).strip() or str(index)
        if step_id in seen_ids:
            raise ValueError(f"步骤 id 重复：{step_id}")
        seen_ids.add(step_id)
        title = str(step.get("title", "")).strip()
        acceptance = str(step.get("acceptance", "")).strip()
        if not title:
            raise ValueError(f"步骤 {step_id} 缺少 title")
        if not acceptance:
            raise ValueError(f"步骤 {step_id} 缺少 acceptance")
        step["id"] = step_id
        step["title"] = title
        step["acceptance"] = acceptance
        if "risky_hint" in step and step["risky_hint"] is not None:
            step["risky_hint"] = str(step["risky_hint"]).strip()
    for key in ("assumptions", "out_of_scope"):
        value = plan.get(key, [])
        if value is None:
            plan[key] = []
        elif not isinstance(value, list):
            raise ValueError(f"字段 {key} 必须是数组")
        else:
            plan[key] = [str(item).strip() for item in value if str(item).strip()]
    plan["goal"] = goal
    plan["steps"] = steps


def plan_summary_text(plan):
    """生成 plan 简短摘要：供 memory_text()、/memory 与 make_plan 工具返回的人类可读部分。"""
    steps = plan.get("steps", [])
    lines = [f"目标: {plan.get('goal', '')}", f"步骤数: {len(steps)}"]
    for step in steps[:6]:
        lines.append(f"  - [{step.get('id')}] {step.get('title')}")
    if len(steps) > 6:
        lines.append(f"  - ...（另有 {len(steps) - 6} 步）")
    return "\n".join(lines)


def format_plan_tool_result(plan):
    """make_plan 工具返回：规划成功 + 摘要 + <plan_json> 块（主循环可把错误当普通 tool 结果处理）。"""
    summary = plan_summary_text(plan)
    payload = json.dumps(plan, ensure_ascii=False, indent=2)
    return f"规划成功\n{summary}\n\n<plan_json>\n{payload}\n</plan_json>"
