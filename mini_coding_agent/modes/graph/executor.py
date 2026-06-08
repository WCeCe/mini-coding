"""DAG 执行引擎（Phase 5.5：通用模板驱动 + verify→generate retry）。"""

import sys

from pathlib import Path

from mini_coding_agent.modes.graph.error_format import format_error_for_model
from mini_coding_agent.modes.graph.nodes import NODE_RUNNERS
from mini_coding_agent.modes.graph.nodes.verify import _modified_python_paths
from mini_coding_agent.modes.graph.session_ctx import observe_post_node, persist_pipeline_session
from mini_coding_agent.modes.graph.verify_rules import collect_tests_snapshot
from mini_coding_agent.modes.graph.types import (
    DagInstance,
    DagNode,
    HarnessContext,
    NodeResult,
    PipelineResult,
)


def execute_dag(agent, dag: DagInstance, user_message: str) -> PipelineResult:
    """按拓扑执行 DAG；verify 失败时按 retry 策略回退 generate。"""
    locate_min = getattr(agent, "_harness_locate_min_snippets", 0) or 0
    ctx = HarnessContext(
        agent=agent,
        dag=dag,
        user_message=user_message,
        test_baseline=collect_tests_snapshot(Path(agent.root)),
        locate_min_snippets_with_source_lines=locate_min,
    )
    order = topological_sort(dag.nodes)
    verify_policy = dag.retry.get("verify")
    verify_retries = 0
    step = 0
    index = 0

    while index < len(order):
        node = order[index]
        step += 1
        runner = NODE_RUNNERS.get(node.type)
        if runner is None:
            return _finish(agent, ctx, PipelineResult(
                ok=False,
                reason=f"节点 type={node.type!r} 尚未实现",
            ))

        if node.type == "generate":
            ctx.generate_attempt = verify_retries

        result = runner(ctx)
        ctx.node_outputs[node.id] = result
        _log_node(dag, step, len(order), node, result)
        observe_post_node(agent, dag, node, result)

        if node.id == "verify" and not result.ok:
            ctx.last_verify_error = format_error_for_model(result.message)
            if verify_policy and verify_retries < verify_policy.max:
                verify_retries += 1
                retry_index = _node_index(order, verify_policy.on_fail)
                if retry_index is None:
                    return _finish(agent, ctx, PipelineResult(ok=False, reason=result.message))
                index = retry_index
                continue
            return _finish(agent, ctx, PipelineResult(ok=False, reason=result.message))

        if not result.ok:
            return _finish(agent, ctx, PipelineResult(ok=False, reason=result.message))

        index += 1

    return _finish(
        agent,
        ctx,
        PipelineResult(ok=True, final_text=_resolve_final(ctx)),
    )


def _finish(agent, ctx: HarnessContext, result: PipelineResult) -> PipelineResult:
    persist_pipeline_session(agent, ctx, result)
    return result


def _resolve_final(ctx: HarnessContext) -> str:
    review = ctx.node_outputs.get("review")
    if review and review.ok:
        return str(review.data.get("final", review.message))
    explain = ctx.node_outputs.get("explain")
    if explain and explain.ok:
        return str(explain.data.get("final", explain.message))
    verify = ctx.node_outputs.get("verify")
    if verify and verify.ok:
        paths = verify.data.get("paths") or _modified_python_paths(ctx)
        if paths:
            return f"已修复并通过验证：{', '.join(paths)}"
        return "已修复并通过验证。"
    return "流水线完成"


def topological_sort(nodes: list[DagNode]) -> list[DagNode]:
    node_map = {node.id: node for node in nodes}
    visited: set[str] = set()
    result: list[DagNode] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        for dep in node_map[node_id].deps:
            visit(dep)
        result.append(node_map[node_id])

    for node in nodes:
        visit(node.id)
    return result


def _node_index(order: list[DagNode], node_id: str) -> int | None:
    for index, node in enumerate(order):
        if node.id == node_id:
            return index
    return None


def _log_node(dag: DagInstance, step: int, total: int, node: DagNode, result: NodeResult) -> None:
    status = "ok" if result.ok else "fail"
    print(
        f"[harness] {dag.intent_id} {step}/{total} {node.type} {status}",
        file=sys.stderr,
        flush=True,
    )
