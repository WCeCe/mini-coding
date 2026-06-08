"""Harness 流水线：Planner + Executor（Phase 5.3）。"""

import sys

from mini_coding_agent.index import ensure_rig
from mini_coding_agent.modes.graph.executor import execute_dag
from mini_coding_agent.modes.graph.harness_trace import record_stage, slots_to_dict
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import DagInstance, PipelineResult


def run_pipeline(agent, intent_id: str, user_message: str, *, skill_name: str | None = None) -> PipelineResult:
    """规划 DAG 并执行；Gate 可选 skill 在 pipeline 前 load_skill。"""
    rig_stats = ensure_rig(agent.root)
    record_stage(agent, "rig", output=dict(rig_stats))
    if rig_stats.get("built"):
        print(
            f"[rig] 已构建索引：{rig_stats['files']} 文件，"
            f"{rig_stats['symbols']} 符号，{rig_stats['imports']} import",
            file=sys.stderr,
            flush=True,
        )
    if skill_name:
        agent.run_tool("load_skill", {"name": skill_name})
    dag = plan(
        intent_id,
        user_message=user_message,
        skill_name=skill_name,
        workspace_root=agent.root,
    )
    record_stage(
        agent,
        "slots",
        input={"user_message": user_message, "intent_id": intent_id},
        output=slots_to_dict(dag.slots),
    )
    return execute_dag(agent, dag, user_message)


def run_pipeline_dag(agent, dag: DagInstance, user_message: str) -> PipelineResult:
    """直接执行已规划的 DagInstance（测试用）。"""
    return execute_dag(agent, dag, user_message)
