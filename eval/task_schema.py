"""tasks.json schema 校验与 L2 管线契约断言。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mini_coding_agent.modes.graph.snippet import has_source_lines

VALID_TIERS = frozenset({"easy", "medium", "hard"})
VALID_GRADINGS = frozenset({"exact", "tests_only"})
VALID_DIMENSIONS = frozenset({
    "retry", "decoy", "gate_boundary", "no_rig", "multi_file",
})
VALID_VERIFY_METHODS = frozenset({"pytest", "py_compile", "lock_tests", "none"})
VALID_ARCH_VERIFY_METHODS = frozenset({"pytest", "py_compile", "lock_tests"})

_GENERATE_ATTEMPT = re.compile(r"\[harness\]\s+\S+\s+\d+/\d+\s+generate\s+", re.IGNORECASE)
_HARNESS_FAIL = re.compile(r"\[harness\].+ (fail)\b", re.IGNORECASE)


@dataclass
class ContractCheck:
    name: str
    passed: bool
    expected: Any
    actual: Any
    message: str = ""


@dataclass
class ContractResult:
    checks: list[ContractCheck] = field(default_factory=list)

    @property
    def pipeline_ok(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[str]:
        return [
            f"{c.name}: expected {c.expected!r}, got {c.actual!r}"
            for c in self.checks
            if not c.passed
        ]


def validate_task(task: dict) -> list[str]:
    """返回校验错误列表；空列表表示合法。"""
    errors: list[str] = []
    task_id = task.get("id", "<unknown>")

    for key in ("id", "tier", "grading", "message", "setup_files", "verify", "harness_intent"):
        if key not in task:
            errors.append(f"缺少必填字段 {key!r}")

    tier = task.get("tier")
    if tier is not None and tier not in VALID_TIERS:
        errors.append(f"tier 无效：{tier!r}")

    grading = task.get("grading")
    if grading is not None and grading not in VALID_GRADINGS:
        errors.append(f"grading 无效：{grading!r}")

    verify = task.get("verify")
    if verify is not None and verify not in VALID_VERIFY_METHODS:
        errors.append(f"verify 无效：{verify!r}")

    dimension = task.get("dimension")
    if dimension is not None and dimension not in VALID_DIMENSIONS:
        errors.append(f"dimension 无效：{dimension!r}")

    if grading == "exact" and not task.get("expect_files"):
        errors.append("grading=exact 须含 expect_files")

    arch = task.get("architecture")
    if arch is not None:
        if not isinstance(arch, dict):
            errors.append("architecture 须为 object")
        else:
            errors.extend(_validate_architecture(arch, task_id))

    fake_script = task.get("fake_script")
    if fake_script is not None:
        if not isinstance(fake_script, list):
            errors.append("fake_script 须为数组")
        else:
            for i, step in enumerate(fake_script):
                if not isinstance(step, dict) or len(step) != 1:
                    errors.append(f"fake_script[{i}] 须为单键步骤对象")

    return errors


def _validate_architecture(arch: dict, task_id: str) -> list[str]:
    errors: list[str] = []
    gate = arch.get("gate")
    if gate is not None and not isinstance(gate, dict):
        errors.append("architecture.gate 须为 object")

    locate = arch.get("locate")
    if locate is not None:
        if not isinstance(locate, dict):
            errors.append("architecture.locate 须为 object")
        elif "must_include_files" in locate and not isinstance(locate["must_include_files"], list):
            errors.append("architecture.locate.must_include_files 须为数组")

    verify_arch = arch.get("verify")
    if verify_arch is not None:
        if not isinstance(verify_arch, dict):
            errors.append("architecture.verify 须为 object")
        else:
            method = verify_arch.get("method")
            if method is not None and method not in VALID_ARCH_VERIFY_METHODS:
                errors.append(f"architecture.verify.method 无效：{method!r}")

    for list_key in ("must_modify", "must_not_modify", "must_not_modify_prefixes"):
        val = arch.get(list_key)
        if val is not None and not isinstance(val, list):
            errors.append(f"architecture.{list_key} 须为数组")

    return errors


def load_tasks(path: Path) -> list[dict]:
    """加载并校验 tasks.json。"""
    tasks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError(f"tasks.json 须为数组：{path}")
    for task in tasks:
        errs = validate_task(task)
        if errs:
            raise ValueError(f"task {task.get('id')}: {errs}")
    return tasks


def tasks_with_fake_script(tasks: list[dict]) -> list[dict]:
    return [t for t in tasks if t.get("fake_script")]


def diff_changed_files(root: Path, setup_files: dict) -> set[str]:
    """相对 setup_files 有内容变更或新增的文件路径集合。"""
    changed: set[str] = set()
    normalized_setup = {
        str(k).replace("\\", "/"): v for k, v in (setup_files or {}).items()
    }
    for rel, expected in normalized_setup.items():
        path = root / rel
        if not path.is_file():
            continue
        if path.read_text(encoding="utf-8") != expected:
            changed.add(rel)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel not in normalized_setup:
            changed.add(rel)
    return changed


def count_generate_attempts(stderr: str) -> int:
    return len(_GENERATE_ATTEMPT.findall(stderr or ""))


def _check(name: str, actual: Any, expected: Any) -> ContractCheck:
    return ContractCheck(name=name, passed=actual == expected, expected=expected, actual=actual)


def _files_from_locate_output(node_outputs: dict | None) -> list[str]:
    if not node_outputs:
        return []
    locate = node_outputs.get("locate") or {}
    data = locate.get("data") or {}
    return list(data.get("files") or [])


def _count_snippets_with_source_lines(node_outputs: dict | None) -> int:
    if not node_outputs:
        return 0
    locate = node_outputs.get("locate") or {}
    snippets = (locate.get("data") or {}).get("snippets") or []
    return sum(1 for s in snippets if has_source_lines(str(s)))


def node_outputs_from_session(session: dict) -> dict | None:
    """从 session.harness_node_outputs 读取可序列化的 node_outputs。"""
    raw = session.get("harness_node_outputs")
    return raw if raw else None


def assert_pipeline_contract(
    task: dict,
    agent: Any,
    stderr: str,
    root: Path,
    *,
    node_outputs: dict | None = None,
) -> ContractResult:
    arch = task.get("architecture") or {}
    checks: list[ContractCheck] = []

    if not arch:
        return ContractResult(checks=[ContractCheck("architecture", True, None, None, "skipped")])

    session = agent.session
    gate = session.get("last_gate") or {}
    last_verify = session.get("last_verify") or {}
    files_touched = session.get("last_files_touched") or []

    if node_outputs is None:
        node_outputs = node_outputs_from_session(session)

    if expected_gate := arch.get("gate"):
        checks.append(_check("gate.route", gate.get("route"), expected_gate.get("route")))
        checks.append(_check("gate.confidence", gate.get("confidence"), expected_gate.get("confidence")))
        if iid := expected_gate.get("intent_id"):
            checks.append(_check("gate.intent_id", gate.get("intent_id"), iid))

    if arch.get("no_open_fallback"):
        checks.append(_check("no_open_fallback", "降级 open" not in (stderr or ""), True))

    if arch.get("pipeline_must_succeed") is True:
        if task.get("dimension") == "retry":
            checks.append(_check("pipeline_must_succeed", "流水线失败" not in (stderr or ""), True))
        else:
            failed_nodes = _HARNESS_FAIL.findall(stderr or "")
            checks.append(_check("pipeline_must_succeed", len(failed_nodes) == 0, True))
    if arch.get("pipeline_must_succeed") is False:
        checks.append(_check("pipeline_must_fail", "fix_bug" not in (stderr or "") or "fail" in (stderr or ""), True))

    if locate_arch := arch.get("locate"):
        must_files = locate_arch.get("must_include_files") or []
        locate_files = _files_from_locate_output(node_outputs) + list(files_touched)
        for f in must_files:
            checks.append(_check(f"locate.must_include.{f}", f in locate_files, True))
        min_snip = locate_arch.get("min_snippets_with_source_lines", 0)
        if min_snip > 0:
            count = _count_snippets_with_source_lines(node_outputs)
            checks.append(_check("locate.min_snippets", count >= min_snip, True))

    if verify_arch := arch.get("verify"):
        expected_method = verify_arch.get("method")
        actual_method = last_verify.get("method")
        if expected_method == "pytest":
            checks.append(_check("verify.method", actual_method, "shell"))
        elif expected_method == "py_compile":
            checks.append(_check("verify.method", actual_method, "py_compile"))

    if max_attempts := arch.get("generate_max_attempts"):
        attempts = count_generate_attempts(stderr)
        checks.append(_check("generate_max_attempts", attempts <= max_attempts, True))

    setup_files = task.get("setup_files") or {}
    normalized_setup = {str(k).replace("\\", "/"): v for k, v in setup_files.items()}
    changed = diff_changed_files(root, setup_files)
    for f in arch.get("must_modify") or []:
        checks.append(_check(f"must_modify.{f}", f in changed, True))
    for f in arch.get("must_not_modify") or []:
        checks.append(_check(f"must_not_modify.{f}", f not in changed, True))
    for prefix in arch.get("must_not_modify_prefixes") or []:
        setup_under = [p for p in normalized_setup if p.startswith(prefix)]
        touched_under = [p for p in changed if p in setup_under]
        checks.append(_check(f"must_not_modify_prefix.{prefix}", len(touched_under) == 0, True))

    return ContractResult(checks=checks)


def apply_harness_contract_hints(agent, task: dict) -> None:
    """将 tasks.json architecture 契约标志注入 agent，供 executor/locate 读取。"""
    arch = task.get("architecture") or {}
    locate_arch = arch.get("locate") or {}
    agent._harness_locate_min_snippets = locate_arch.get("min_snippets_with_source_lines", 0)


def _guided_patch_tool_output(path: str, new_text: str) -> str:
    """Phase 7.2：模型只产 path + new_text（系统注入 old_text）。"""
    return (
        '<tool>{"name":"patch_file","args":'
        f'{{"path":{json.dumps(path)},"new_text":{json.dumps(new_text)}}}'
        "}</tool>"
    )


def _write_tool_output(path: str, content: str) -> str:
    return (
        '<tool>{"name":"write_file","args":'
        f'{{"path":{json.dumps(path)},"content":{json.dumps(content)}}}'
        "}</tool>"
    )


def fake_script_to_outputs(fake_script: list[dict]) -> list[str]:
    """将 tasks.json fake_script 步骤转为 FakeModelClient 预设输出队列。"""
    outputs: list[str] = []
    for step in fake_script:
        if "gate" in step:
            g = step["gate"]
            payload: dict[str, Any] = {
                "intent_id": g.get("intent_id", "fix_bug"),
                "confidence": g.get("confidence", "high"),
            }
            if g.get("skill"):
                payload["skill"] = g["skill"]
            outputs.append(json.dumps(payload))
        elif "patch" in step:
            p = step["patch"]
            outputs.append(_guided_patch_tool_output(p["path"], p["new_text"]))
        elif "write" in step:
            w = step["write"]
            outputs.append(_write_tool_output(w["path"], w["content"]))
        elif "final" in step:
            outputs.append(f"<final>{step['final']}</final>")
        elif "raw" in step:
            outputs.append(step["raw"])
    return outputs
