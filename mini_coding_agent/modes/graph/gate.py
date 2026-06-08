"""LLM 意图分类 Gate（Phase 5.1）：每 ask 一次 complete；调模型 → 解析 JSON → 产出 GateResult。"""
import json

from mini_coding_agent.modes.graph.gate_prompt import build_gate_prompt
from mini_coding_agent.modes.graph.types import (
    GATE_MAX_NEW_TOKENS,
    INTENT_IDS,
    Confidence,
    GateResult,
    Route,
)
from mini_coding_agent.platform.planning import extract_json_object
from mini_coding_agent.platform.wait_display import complete_with_wait_display

MESSAGE_GATE = "正在分类用户意图…"


def classify_gate(model_client, user_message: str, *, max_new_tokens: int = GATE_MAX_NEW_TOKENS) -> GateResult:
    """调用模型一次，解析 Gate JSON；解析失败或非法 intent → confidence=low, route=open。"""
    prompt = build_gate_prompt(user_message)
    raw = complete_with_wait_display(
        model_client,
        prompt,
        max_new_tokens,
        message=MESSAGE_GATE,
    )
    return parse_gate_response(raw)


def parse_gate_response(raw: str) -> GateResult:
    """解析 Gate JSON；规则兜底：解析失败 / 非法 intent → low + open。"""
    raw_text = str(raw).strip()
    try:
        payload = json.loads(extract_json_object(raw_text))
    except (ValueError, json.JSONDecodeError):
        return GateResult(
            intent_id="",
            confidence="low",
            route="open",
            raw=raw_text or None,
        )

    if not isinstance(payload, dict):
        return GateResult(intent_id="", confidence="low", route="open", raw=raw_text)

    intent_id = str(payload.get("intent_id", "")).strip()
    confidence_raw = str(payload.get("confidence", "")).strip().lower()
    confidence: Confidence = "high" if confidence_raw == "high" else "low"

    skill = payload.get("skill")
    if skill is not None and skill != "":
        skill = str(skill).strip() or None
    else:
        skill = None

    if intent_id not in INTENT_IDS:
        return GateResult(
            intent_id=intent_id,
            confidence="low",
            route="open",
            skill=skill,
            raw=raw_text,
        )

    route: Route = "harness_pipeline" if confidence == "high" else "open"
    return GateResult(
        intent_id=intent_id,
        confidence=confidence,
        route=route,
        skill=skill,
        raw=raw_text,
    )
