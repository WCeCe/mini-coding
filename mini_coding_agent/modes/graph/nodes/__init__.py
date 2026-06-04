"""Harness 节点注册表（Phase 5.5：七类 type）。"""

from mini_coding_agent.modes.graph.nodes.explain import run_explain
from mini_coding_agent.modes.graph.nodes.generate import run_generate
from mini_coding_agent.modes.graph.nodes.locate import run_locate
from mini_coding_agent.modes.graph.nodes.ops import run_ops
from mini_coding_agent.modes.graph.nodes.plan import run_plan
from mini_coding_agent.modes.graph.nodes.review import run_review
from mini_coding_agent.modes.graph.nodes.verify import run_verify

NODE_RUNNERS = {
    "locate": run_locate,
    "plan": run_plan,
    "generate": run_generate,
    "verify": run_verify,
    "review": run_review,
    "explain": run_explain,
    "ops": run_ops,
}
