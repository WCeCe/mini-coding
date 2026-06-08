"""Graph Harness 编排入口（Phase 5.1 Gate + 5.5 五类 pipeline）。

--harness off：完全 bypass，直接 open loop
--harness on：先 Gate，再走 pipeline；失败降级 agent.ask(message)
--gate-log：只打 Gate 日志，可以不跑 pipeline
"""
import sys

from mini_coding_agent.modes.graph.gate import classify_gate
from mini_coding_agent.modes.graph.pipeline import run_pipeline
from mini_coding_agent.modes.graph.session_ctx import persist_last_gate
from mini_coding_agent.modes.graph.types import PIPELINE_INTENTS_V1, GateResult


def format_gate_log_line(result: GateResult) -> str:
    """Gate 观测行（stderr，中文标签 + 英文字段值）。"""
    skill_part = result.skill if result.skill else "（无）"
    return (
        f"[gate] intent_id={result.intent_id or '（空）'} "
        f"confidence={result.confidence} route={result.route} skill={skill_part}"
    )


def _persist_last_gate(agent, result: GateResult) -> None:
    persist_last_gate(agent, result.to_session_dict())


def handle_ask(agent, message: str, *, harness_enabled: bool = False, gate_log: bool = False) -> str:
    """Harness 入口：Gate → 五类 pipeline 或 open 降级。"""
    if not harness_enabled and not gate_log:
        return agent.ask(message)

    result = classify_gate(agent.model_client, message)
    _persist_last_gate(agent, result)

    if gate_log:
        print(format_gate_log_line(result), file=sys.stderr, flush=True)

    if harness_enabled and result.route == "harness_pipeline":
        if result.intent_id in PIPELINE_INTENTS_V1:
            pipeline_result = run_pipeline(
                agent,
                result.intent_id,
                message,
                skill_name=result.skill,
            )
            if pipeline_result.ok:
                return pipeline_result.final_text
            print(
                f"[harness] 流水线失败：{pipeline_result.reason}，降级 open",
                file=sys.stderr,
                flush=True,
            )
            return agent.ask(message)

    return agent.ask(message)
