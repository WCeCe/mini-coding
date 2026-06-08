"""Harness 阶段追踪：记录 gate / rig / slots / locate / generate / verify 的 input 与 output。"""

from __future__ import annotations

from mini_coding_agent.modes.graph.types import HarnessContext, NodeResult

HARNESS_TRACE_KEY = "harness_trace"


def clear_trace(agent) -> None:
    """新一轮 ask 前清空追踪列表。"""
    agent.session[HARNESS_TRACE_KEY] = []


def get_trace(agent) -> list[dict]:
    """返回当前 session 中的阶段追踪列表（只读副本）。"""
    raw = agent.session.get(HARNESS_TRACE_KEY)
    if not isinstance(raw, list):
        return []
    return list(raw)


def record_stage(
    agent,
    stage: str,
    *,
    input: dict | None = None,
    output: dict | None = None,
    meta: dict | None = None,
) -> None:
    """追加一条阶段记录；直接写入 agent.session。"""
    trace = agent.session.get(HARNESS_TRACE_KEY)
    if not isinstance(trace, list):
        trace = []
        agent.session[HARNESS_TRACE_KEY] = trace
    entry: dict = {"stage": stage}
    if input is not None:
        entry["input"] = input
    if output is not None:
        entry["output"] = output
    if meta:
        entry["meta"] = meta
    trace.append(entry)


def slots_to_dict(slots) -> dict:
    """DagSlots → 可 JSON 序列化的 dict。"""
    data = {
        "goal": slots.goal,
        "files_hint": list(slots.files_hint),
        "symbols_hint": list(slots.symbols_hint),
    }
    if slots.test_command:
        data["test_command"] = slots.test_command
    if slots.skill_name:
        data["skill_name"] = slots.skill_name
    return data


def record_node_stage(agent, node_type: str, ctx: HarnessContext, result: NodeResult) -> None:
    """非 LLM 节点（locate / verify 等）的 input/output 记录。"""
    if node_type == "locate":
        record_stage(
            agent,
            "locate",
            input={"slots": slots_to_dict(ctx.dag.slots)},
            output={
                "ok": result.ok,
                "message": result.message,
                "files": list(result.data.get("files") or []),
                "snippets": list(result.data.get("snippets") or []),
                "used_rig": bool(result.data.get("used_rig")),
                "symbols_hint": list(result.data.get("symbols_hint") or []),
            },
        )
        return

    if node_type == "verify":
        record_stage(
            agent,
            "verify",
            input={"intent_id": ctx.dag.intent_id, "generate_attempt": ctx.generate_attempt},
            output={
                "ok": result.ok,
                "message": result.message,
                "data": dict(result.data),
            },
        )
