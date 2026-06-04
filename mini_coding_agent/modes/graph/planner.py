"""DAG 模板加载与 Planner（Phase 5.2）。"""

import json
from copy import deepcopy
from pathlib import Path

from mini_coding_agent.modes.graph.slots import fill_slots
from mini_coding_agent.modes.graph.types import (
    DagInstance,
    DagNode,
    DagSlots,
    INTENT_IDS,
    NODE_TYPES,
    RetryPolicy,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def plan(
    intent_id: str,
    *,
    user_message: str,
    skill_name: str | None = None,
    workspace_root: str | Path | None = None,
) -> DagInstance:
    """按 intent_id 加载静态模板并填充槽位，产出 DagInstance。"""
    if intent_id not in INTENT_IDS:
        raise ValueError(f"不支持的 intent_id：{intent_id}")

    template = load_template(intent_id)
    slots_data = fill_slots(
        user_message,
        intent_id=intent_id,
        skill_name=skill_name,
        workspace_root=workspace_root,
    )
    return DagInstance(
        intent_id=template["intent_id"],
        nodes=deepcopy(template["nodes"]),
        slots=DagSlots(**slots_data),
        retry=deepcopy(template.get("retry", {})),
    )


def load_template(intent_id: str) -> dict:
    """加载并校验模板 JSON；intent_id 须与文件名一致。"""
    if intent_id not in INTENT_IDS:
        raise ValueError(f"不支持的 intent_id：{intent_id}")

    path = TEMPLATES_DIR / f"{intent_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"缺少模板文件：{path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    _validate_template(data, intent_id, path)
    return {
        "intent_id": data["intent_id"],
        "nodes": [_parse_node(item) for item in data["nodes"]],
        "retry": _parse_retry(data.get("retry", {})),
    }


def list_template_intents() -> list[str]:
    """返回已注册模板 intent_id 列表（与 INTENT_IDS 一一对应）。"""
    return sorted(INTENT_IDS)


def _validate_template(data: dict, intent_id: str, path: Path) -> None:
    if not isinstance(data, dict):
        raise ValueError(f"模板格式无效：{path}")
    if data.get("intent_id") != intent_id:
        raise ValueError(f"模板 intent_id 与文件名不一致：{path}")
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError(f"模板 nodes 无效：{path}")
    seen_ids: set[str] = set()
    for item in nodes:
        if not isinstance(item, dict):
            raise ValueError(f"模板节点必须是对象：{path}")
        node_id = str(item.get("id", "")).strip()
        node_type = str(item.get("type", "")).strip()
        if not node_id or node_id in seen_ids:
            raise ValueError(f"模板节点 id 无效或重复：{path}")
        if node_type not in NODE_TYPES:
            raise ValueError(f"未知节点 type={node_type!r}：{path}")
        seen_ids.add(node_id)
        deps = item.get("deps", [])
        if not isinstance(deps, list):
            raise ValueError(f"模板节点 deps 必须是数组：{path}")


def _parse_node(item: dict) -> DagNode:
    return DagNode(
        id=str(item["id"]),
        type=str(item["type"]),
        deps=[str(dep) for dep in item.get("deps", [])],
    )


def _parse_retry(raw: dict) -> dict[str, RetryPolicy]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, RetryPolicy] = {}
    for node_id, policy in raw.items():
        if not isinstance(policy, dict):
            continue
        on_fail = str(policy.get("on_fail", "")).strip()
        max_retries = int(policy.get("max", 0))
        if on_fail and max_retries > 0:
            result[str(node_id)] = RetryPolicy(on_fail=on_fail, max=max_retries)
    return result
