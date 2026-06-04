"""Harness 流水线：Planner + Executor（Phase 5.3）。"""

from mini_coding_agent.modes.graph.executor import execute_dag
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import DagInstance, PipelineResult


def run_pipeline(agent, intent_id: str, user_message: str, *, skill_name: str | None = None) -> PipelineResult:
    """规划 DAG 并执行；Gate 可选 skill 在 pipeline 前 load_skill。"""
    if skill_name:
        agent.run_tool("load_skill", {"name": skill_name})
    dag = plan(
        intent_id,
        user_message=user_message,
        skill_name=skill_name,
        workspace_root=agent.root,
    )
    return execute_dag(agent, dag, user_message)


def run_pipeline_dag(agent, dag: DagInstance, user_message: str) -> PipelineResult:
    """直接执行已规划的 DagInstance（测试用）。"""
    return execute_dag(agent, dag, user_message)
