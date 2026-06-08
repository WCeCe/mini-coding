"""Graph Harness 共享类型（Phase 5 Gate / Planner）。"""

from dataclasses import dataclass, field
from typing import Literal, Optional

# 封闭五类意图；与 struct/phase5-graph-harness.md §5.1 一致
INTENT_IDS = frozenset(
    {
        "generate_code",
        "fix_bug",
        "refactor",
        "explain",
        "project_ops",
    }
)

# struct §7 节点 type 枚举
NODE_TYPES = frozenset(
    {
        "locate",
        "generate",
        "verify",
        "review",
        "plan",
        "explain",
        "ops",
    }
)

Confidence = Literal["high", "low"]
Route = Literal["open", "harness_pipeline"]

GATE_MAX_NEW_TOKENS = 256
GOAL_MAX_LEN = 300

# project_ops 默认 shell 白名单（节点实现时校验；Planner 写入槽位）
DEFAULT_OPS_ALLOWLIST = (
    "pytest",
    "python -m pytest",
    "pip install",
    "pip list",
    "git status",
    "git diff",
    "git log",
)

"""llm的gate输出"""
@dataclass
class GateResult:
    #五类意图的哪一个
    intent_id: str
    #可信度高还是低
    confidence: Confidence
    #走pipeline还是open
    route: Route
    skill: Optional[str] = None
    raw: Optional[str] = None

    def to_session_dict(self) -> dict:
        """写入 session JSON 的 last_gate 字段。"""
        data = {
            "intent_id": self.intent_id,
            "confidence": self.confidence,
            "route": self.route,
        }
        if self.skill is not None:
            data["skill"] = self.skill
        return data

"""DAG的上一个节点"""
@dataclass
class DagNode:
    id: str
    type: str
    deps: list[str] = field(default_factory=list)


@dataclass
class RetryPolicy:
    on_fail: str
    max: int

"""DAG的槽位"""
@dataclass
class DagSlots:
    goal: str
    files_hint: list[str] = field(default_factory=list)
    symbols_hint: list[str] = field(default_factory=list)
    test_command: Optional[str] = None
    skill_name: Optional[str] = None
    ops_allowlist: Optional[list[str]] = None

"""一次流水线的完整示例"""
@dataclass
class DagInstance:
    intent_id: str
    nodes: list[DagNode]
    slots: DagSlots
    retry: dict[str, RetryPolicy] = field(default_factory=dict)

    def node_types(self) -> list[str]:
        return [node.type for node in self.nodes]


@dataclass
class NodeResult:
    ok: bool
    message: str
    data: dict = field(default_factory=dict)

"""「整条流水线 / 整个任务」的执行上下文"""
@dataclass
class HarnessContext:
    agent: object
    dag: DagInstance
    user_message: str
    node_outputs: dict[str, NodeResult] = field(default_factory=dict)
    generate_attempt: int = 0
    last_verify_error: str = ""
    test_baseline: dict[str, str] = field(default_factory=dict)
    locate_min_snippets_with_source_lines: int = 0


@dataclass
class PipelineResult:
    ok: bool
    final_text: str = ""
    reason: str = ""


# 5.5：五类意图均走 harness pipeline（high + 合法 intent）
PIPELINE_INTENTS_V1 = frozenset(INTENT_IDS)
