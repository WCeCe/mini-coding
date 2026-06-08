# L2 管线契约 Eval 规格

> 返回索引：[`README.md`](./README.md) · Schema：[`03-task-schema.md`](./03-task-schema.md)

L2 用 **FakeModel + tasks.json** 断言整条 fix_bug DAG 是否按 `architecture` 契约执行，并与 grading 终判组成 **`pipeline_ok` + `outcome_ok`** 双断言。

---

## 1. 目标文件

| 文件 | 职责 |
|------|------|
| `tests/test_eval_contract.py` | parametrized 契约测试入口 |
| `eval/task_schema.py` | `validate_task`, `assert_pipeline_contract`, helpers |
| `eval/tasks.json` | 含 `fake_script` 的任务为数据源 |

---

## 2. 测试流程

```
load_tasks_with_fake_script()
  → for each task:
      1. tmp_path + setup_task_workspace(root, task)
      2. agent = MiniAgent(..., FakeModelClient(task["fake_script"]))
      3. stderr = capture_stderr(handle_ask, agent, message, harness_enabled=True)
      4. contract = assert_pipeline_contract(task, agent, stderr, root)
      5. grading_err, _ = check_task_grading(root, task)
      6. assert contract.pipeline_ok
      7. assert grading_err is None
```

### 2.1 FakeModelClient 行为（规划）

队列消费 `fake_script` 每一步：

| 步骤类型 | 响应给 |
|----------|--------|
| `gate` | Gate 的 `complete()` |
| `patch` / `write` / `final` / `raw` | Generate（及 Review 若需要）的 `complete()` |

Generate 步将 `patch` 转为标准 tool XML/JSON 字符串，与现有 `FakeModelClient` harness 测试对齐。

---

## 3. ContractResult 数据结构

```python
@dataclass
class ContractCheck:
    name: str          # 如 "gate.route"
    passed: bool
    expected: Any
    actual: Any
    message: str = ""


@dataclass
class ContractResult:
    checks: list[ContractCheck]

    @property
    def pipeline_ok(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[str]:
        return [f"{c.name}: expected {c.expected!r}, got {c.actual!r}" for c in self.checks if not c.passed]
```

---

## 4. assert_pipeline_contract 逐项断言

```python
def assert_pipeline_contract(
    task: dict,
    agent: MiniAgent,
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

    # --- Gate ---
    if expected_gate := arch.get("gate"):
        checks.append(_check("gate.route", gate.get("route"), expected_gate.get("route")))
        checks.append(_check("gate.confidence", gate.get("confidence"), expected_gate.get("confidence")))
        if iid := expected_gate.get("intent_id"):
            checks.append(_check("gate.intent_id", gate.get("intent_id"), iid))

    # --- Open fallback ---
    if arch.get("no_open_fallback"):
        checks.append(_check("no_open_fallback", "降级 open" not in stderr, True))

    # --- Pipeline ok（executor 层）---
    if arch.get("pipeline_must_succeed") is True:
        failed_nodes = re.findall(r"\[harness\].+ (fail)\b", stderr)
        checks.append(_check("pipeline_must_succeed", len(failed_nodes) == 0, True))
    if arch.get("pipeline_must_succeed") is False:
        # B3 gate_boundary：不应出现 fix_bug harness 成功
        checks.append(_check("pipeline_must_fail", "fix_bug" not in stderr or "fail" in stderr, True))

    # --- Locate ---
    if locate_arch := arch.get("locate"):
        must_files = locate_arch.get("must_include_files") or []
        locate_files = _files_from_locate_output(node_outputs) + files_touched
        for f in must_files:
            checks.append(_check(f"locate.must_include.{f}", f in locate_files, True))
        min_snip = locate_arch.get("min_snippets_with_source_lines", 0)
        if min_snip > 0:
            count = _count_snippets_with_source_lines(node_outputs)
            checks.append(_check("locate.min_snippets", count >= min_snip, True))

    # --- Verify method ---
    if verify_arch := arch.get("verify"):
        expected_method = verify_arch.get("method")
        actual_method = last_verify.get("method")
        if expected_method == "pytest":
            checks.append(_check("verify.method", actual_method, "shell"))
        elif expected_method == "py_compile":
            checks.append(_check("verify.method", actual_method, "py_compile"))

    # --- Generate attempts ---
    if max_attempts := arch.get("generate_max_attempts"):
        attempts = _count_generate_attempts(stderr)
        checks.append(_check("generate_max_attempts", attempts <= max_attempts, True))

    # --- File diff ---
    changed = diff_changed_files(root, task.get("setup_files") or {})
    for f in arch.get("must_modify") or []:
        checks.append(_check(f"must_modify.{f}", f in changed, True))
    for f in arch.get("must_not_modify") or []:
        checks.append(_check(f"must_not_modify.{f}", f not in changed, True))
    for prefix in arch.get("must_not_modify_prefixes") or []:
        touched_under = [p for p in changed if p.startswith(prefix)]
        checks.append(_check(f"must_not_modify_prefix.{prefix}", len(touched_under) == 0, True))

    return ContractResult(checks=checks)
```

### 4.1 Helper 函数

```python
def _count_generate_attempts(stderr: str) -> int:
    return len(re.findall(r"\[harness\]\s+\S+\s+\d+/\d+\s+generate\s+", stderr))


def diff_changed_files(root: Path, setup_files: dict) -> set[str]:
    changed = set()
    for rel, expected in setup_files.items():
        path = root / rel
        if not path.is_file():
            continue
        if path.read_text(encoding="utf-8") != expected:
            changed.add(rel.replace("\\", "/"))
    # 新增文件
    for path in root.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(root)).replace("\\", "/")
            if rel not in setup_files:
                changed.add(rel)
    return changed


_SNIPPET_LINE = re.compile(r"# .+\.py:\d+")


def _count_snippets_with_source_lines(node_outputs: dict | None) -> int:
    if not node_outputs:
        return 0
    locate = node_outputs.get("locate") or {}
    snippets = (locate.get("data") or {}).get("snippets") or []
    return sum(1 for s in snippets if _SNIPPET_LINE.search(str(s)))
```

### 4.2 获取 node_outputs

契约测试需读取 locate 中间结果。实现选项（择一）：

| 方案 | 做法 | 优缺点 |
|------|------|--------|
| A | executor 测试 hook 暴露 `ctx.node_outputs` | 最准；需小改 executor |
| B | 从 stderr + session 推断 | 无改码；locate snippet 断言弱 |
| C | 直接调用 `run_locate` 单测 + L2 只测 DAG 后半 | 拆分；L2 不完整 |

**推荐 P0-b**：方案 A——在 `handle_ask` 或 executor 返回 `PipelineResult` 时附带 `node_outputs`（仅测试用或 session 字段）。

---

## 5. 首批三条契约任务

### 5.1 nameerror_calc

| 断言项 | 期望值 |
|--------|--------|
| gate.route | harness_pipeline |
| no_open_fallback | true |
| locate.must_include.calc.py | true |
| must_modify.calc.py | true |
| verify.method | py_compile |
| outcome | exact match expect_files |

### 5.2 off_by_one_sum

| 断言项 | 期望值 |
|--------|--------|
| verify.method | shell (pytest) |
| must_modify.sum_first.py | true |
| must_not_modify_prefix.tests/ | true |
| lock_tests | pass |
| outcome | tests_only pass |

### 5.3 import_chain_rate

| 断言项 | 期望值 |
|--------|--------|
| must_modify.rates.py | true |
| must_not_modify.app.py（可选） | app 未改或仅读 |
| locate.must_include.rates.py | true |
| outcome | tests_only pass |

---

## 6. 失败时的输出

```python
assert contract.pipeline_ok, "\n".join(contract.failures)
```

示例：

```
gate.route: expected 'harness_pipeline', got 'open'
must_modify.rates.py: expected True, got False
no_open_fallback: expected True, got False
```

---

## 7. CI 集成

```bash
python -m pytest tests/test_eval_contract.py -v
```

与 `test_eval_runner.py` 同 job，零 LLM。

---

## 8. Done Definition（L2）

- [ ] `eval/task_schema.py` 或等价模块存在
- [ ] `assert_pipeline_contract` 实现上述断言项
- [ ] ≥3 任务含 `architecture` + `fake_script`
- [ ] `test_eval_contract.py` parametrized 全绿
- [ ] 失败信息可定位到 `ContractCheck.name`

---

*07-l2-contract-spec.md · 波次 D · 2026-06-05*
