"""Harness 跨 ask 会话字段（Phase 5.6）。

写入 agent.session JSON：
- last_gate（Gate 结果，runner 更新）
- last_files_touched（流水线触及文件）
- last_verify（最近一次 verify 摘要）
- harness_last_node（可选观测：末节点，observe-only）
"""

from mini_coding_agent.modes.graph.types import DagInstance, DagNode, HarnessContext, NodeResult, PipelineResult
from mini_coding_agent.platform.util import clip

HARNESS_SESSION_KEYS = (
    "last_gate",
    "last_files_touched",
    "last_verify",
    "harness_last_node",
    "harness_node_outputs",
)

FILES_TOUCHED_LIMIT = 8


def empty_harness_fields() -> dict:
    return {
        "last_gate": None,
        "last_files_touched": [],
        "last_verify": None,
        "harness_last_node": None,
        "harness_node_outputs": None,
    }


def ensure_harness_session_shape(session: dict) -> None:
    """旧 session 兼容：补齐 harness 字段。"""
    session.setdefault("last_gate", None)
    session.setdefault("last_files_touched", [])
    session.setdefault("last_verify", None)
    session.setdefault("harness_last_node", None)
    session.setdefault("harness_node_outputs", None)


def clear_harness_session(session: dict) -> None:
    """/reset 时清空 harness 相关字段。"""
    session.update(empty_harness_fields())


def get_harness_context(session: dict) -> dict:
    """供 Gate/Planner 读取的上一轮 harness 快照（只读）。"""
    ensure_harness_session_shape(session)
    return {
        "last_gate": session.get("last_gate"),
        "last_files_touched": list(session.get("last_files_touched") or []),
        "last_verify": session.get("last_verify"),
    }


def persist_last_gate(agent, gate_dict: dict) -> None:
    ensure_harness_session_shape(agent.session)
    agent.session["last_gate"] = gate_dict
    _save(agent)


def persist_pipeline_session(agent, ctx: HarnessContext, pipeline_result: PipelineResult) -> None:
    """流水线结束后写入 last_files_touched / last_verify / harness_node_outputs。"""
    ensure_harness_session_shape(agent.session)
    agent.session["last_files_touched"] = _collect_files_touched(ctx)
    agent.session["last_verify"] = _summarize_verify(ctx, pipeline_result)
    agent.session["harness_node_outputs"] = _serialize_node_outputs(ctx)
    _save(agent)


def _serialize_node_outputs(ctx: HarnessContext) -> dict:
    result: dict = {}
    for node_id, nr in ctx.node_outputs.items():
        result[node_id] = {
            "ok": nr.ok,
            "message": nr.message,
            "data": dict(nr.data),
        }
    return result


def observe_post_node(agent, dag: DagInstance, node: DagNode, result: NodeResult) -> None:
    """observe-only：记录末节点观测；异常 fail-open，不阻断 executor。"""
    try:
        ensure_harness_session_shape(agent.session)
        agent.session["harness_last_node"] = {
            "intent_id": dag.intent_id,
            "node_id": node.id,
            "type": node.type,
            "ok": result.ok,
        }
        _save(agent)
    except Exception:
        return


def _collect_files_touched(ctx: HarnessContext) -> list[str]:
    seen: set[str] = set()
    files: list[str] = []

    def add(path: str | None) -> None:
        if not path:
            return
        rel = str(path).replace("\\", "/").strip()
        if rel and rel not in seen:
            seen.add(rel)
            files.append(rel)

    generate = ctx.node_outputs.get("generate")
    if generate and generate.ok:
        add(generate.data.get("path"))

    locate = ctx.node_outputs.get("locate")
    if locate:
        for hint in locate.data.get("files", []):
            add(hint)

    return files[:FILES_TOUCHED_LIMIT]


def _summarize_verify(ctx: HarnessContext, pipeline_result: PipelineResult) -> dict | None:
    verify = ctx.node_outputs.get("verify")
    if verify:
        return {
            "ok": verify.ok,
            "method": verify.data.get("method"),
            "summary": clip(verify.message, 220),
        }
    if not pipeline_result.ok:
        return {
            "ok": False,
            "method": None,
            "summary": clip(pipeline_result.reason or "流水线失败", 220),
        }
    return None


def _save(agent) -> None:
    agent.session_path = agent.session_store.save(agent.session)
