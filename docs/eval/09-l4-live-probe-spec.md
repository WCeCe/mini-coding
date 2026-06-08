# L4 Live 能力探针规格

> 返回索引：[`README.md`](./README.md) · failure_type：[`04-failure-taxonomy.md`](./04-failure-taxonomy.md)

在现有 `eval/run_eval.py` 上扩展报告与 CLI，不替换主框架。L4 回答：**真实 Ollama 模型下，fix_bug harness 够不够用？**

---

## 1. 现有能力（波次 C，已实现）

| 能力 | 实现位置 |
|------|----------|
| Ollama live 跑任务 | `run_single_task()` |
| grading 终判 | `check_task_grading()` |
| failure_step 推断 | `infer_failure_step()` |
| steps[] 解析 | `parse_harness_steps()` |
| 基线 save/compare | `save_baseline()`, `format_compare_report()` |
| tier / grading 字段 | `TaskResult` |

---

## 2. 规划扩展（P0-a）

### 2.1 TaskResult 新字段

```python
@dataclass
class TaskResult:
    task_id: str
    passed: bool
    # --- 新增 ---
    pipeline_ok: bool | None = None      # None = 无 architecture 契约
    outcome_ok: bool = False
    failure_type: str | None = None
    observability: dict = field(default_factory=dict)
    # --- 现有 ---
    failure_step: str | None = None
    reason: str | None = None
    elapsed_ms: float = 0.0
    harness_stderr: str = field(default="", repr=False)
    steps: list[dict] = field(default_factory=list)
    tier: str | None = None
    grading: str | None = None
```

### 2.2 observability 结构

```json
{
  "gate": {
    "intent_id": "fix_bug",
    "confidence": "high",
    "route": "harness_pipeline",
    "skill": null
  },
  "last_verify": {
    "ok": true,
    "method": "shell",
    "summary": "pytest 通过"
  },
  "harness_last_node": {
    "intent_id": "fix_bug",
    "node_id": "verify",
    "type": "verify",
    "ok": true
  },
  "files_touched": ["calc.py"],
  "open_fallback": false,
  "generate_attempts": 1
}
```

#### 2.2.1 读取点（run_single_task 内）

在 `handle_ask` 返回后、终判前：

```python
session = agent.session
observability = {
    "gate": session.get("last_gate"),
    "last_verify": session.get("last_verify"),
    "harness_last_node": session.get("harness_last_node"),
    "files_touched": session.get("last_files_touched") or [],
    "open_fallback": "降级 open" in stderr_text,
    "generate_attempts": _count_generate_attempts(stderr_text),
}
```

### 2.3 passed 语义

```python
def compute_passed(
    outcome_ok: bool,
    pipeline_ok: bool | None,
    open_fallback: bool,
    *,
    strict_pipeline: bool = False,
) -> bool:
    if open_fallback:
        return False
    if strict_pipeline and pipeline_ok is not None:
        return outcome_ok and pipeline_ok
    return outcome_ok
```

| 模式 | passed 条件 |
|------|-------------|
| 默认 | `outcome_ok` 且非 `open_fallback` |
| `--strict-pipeline` | 上述 + `pipeline_ok == True`（有 architecture 时） |

### 2.4 新 CLI 选项

```
--strict-pipeline     passed 同时要求 pipeline_ok
--report json         JSON 含新字段（已有 report 扩展）
```

---

## 3. infer_failure_type 集成

见 [`04-failure-taxonomy.md`](./04-failure-taxonomy.md) §3。

`run_single_task` 末尾：

```python
outcome_err, step_hint = check_task_grading(root, task)
outcome_ok = outcome_err is None

pipeline_ok = None
if task.get("architecture"):
    contract = assert_pipeline_contract(task, agent, stderr_text, root)
    pipeline_ok = contract.pipeline_ok

failure_type = infer_failure_type(
    agent.session,
    stderr_text,
    outcome_err,
    task,
    outcome_ok=outcome_ok,
    pipeline_ok=pipeline_ok,
)
failure_step = infer_failure_step(stderr_text, expect_error=outcome_err)
```

---

## 4. 报告格式

### 4.1 Markdown（单任务失败段）

```markdown
### ❌ import_chain_rate (medium, tests_only)

- **passed**: false
- **outcome_ok**: false
- **pipeline_ok**: false
- **failure_type**: locate_wrong_file
- **failure_step**: locate
- **reason**: pytest 失败：…
- **elapsed**: 45230 ms

**分步**: gate:ok → locate:ok → generate:ok → verify:fail

**observability**:
- gate: intent_id=fix_bug confidence=high route=harness_pipeline
- files_touched: ["app.py"]
- generate_attempts: 1
- open_fallback: false
```

### 4.2 Markdown（汇总尾）

```markdown
## Summary

| 指标 | 值 |
|------|-----|
| passed | 2/15 |
| outcome_ok | 3/15 |
| pipeline_ok（有契约任务） | 2/3 |

## 架构痛点聚合（failure_type）

| failure_type | 数量 | 任务 |
|--------------|------|------|
| generate_patch_match | 5 | … |

## 建议优先改动

1. `nodes/generate.py` — 5 条 generate_patch_match
2. `nodes/locate.py` — 2 条 locate_wrong_file
```

### 4.3 JSON

```json
{
  "mode": "live",
  "model": "qwen2.5-coder:7b",
  "summary": {
    "passed": 2,
    "total": 15,
    "outcome_ok": 3,
    "pipeline_ok": 2,
    "pipeline_ok_total": 3,
    "failure_types": {
      "generate_patch_match": 5,
      "locate_wrong_file": 2
    }
  },
  "tasks": [ { "...": "TaskResult 全字段" } ]
}
```

### 4.4 基线对比扩展

`--compare` 除 passed 外，可选报告：

- 新增 `failure_type` 变化
- `pipeline_ok` 回归

---

## 5. 工作流

### 5.1 日常迭代

```bash
# 1. 改代码前：CI 绿（L1–L3）
python -m pytest tests/diagnostic/ tests/test_eval_contract.py tests/test_harness_*.py -q

# 2. 改 generate 后：单条 live 试跑
python eval/run_eval.py --task nameerror_calc

# 3. 全量 + 对比基线
python eval/run_eval.py --compare eval/baselines/live-qwen2.5-coder-7b.json

# 4. 看 failure_type 聚合，只改对应节点

# 5. 根因明确 → 写 QA_LOG + regression test
```

### 5.2 冻结基线更新

仅当 intentionally 接受行为变更时更新 baselines：

```bash
python eval/run_eval.py --save-baseline eval/baselines/live-qwen2.5-coder-7b.json
```

须在 commit message 或 QA_LOG 记录原因。

---

## 6. 与 L2 的字段对齐

| 字段 | L2 契约测 | L4 live |
|------|-----------|---------|
| pipeline_ok | assert | 有 architecture 则计算 |
| outcome_ok | assert | check_task_grading |
| failure_type | 失败时推断 | 同函数 |
| observability | 可选 | 总是收集 |

共用 `eval/task_schema.py` 中的 `assert_pipeline_contract` 与 `infer_failure_type`。

---

## 7. test_eval_runner.py 扩展（无 Ollama）

| 测试 | 内容 |
|------|------|
| `test_infer_failure_type_gate_low` | mock session |
| `test_infer_failure_type_patch_match` | stderr 样本 |
| `test_task_result_to_dict_new_fields` | JSON 序列化 |
| `test_compute_passed_strict_pipeline` | CLI 语义 |
| `test_format_report_failure_type_aggregate` | 聚合 Markdown |

---

## 8. Done Definition（L4 报告增强）

- [ ] `TaskResult` / `task_result_to_dict` 含新字段
- [ ] `run_single_task` 读取 session observability
- [ ] `infer_failure_type` 实现 + 测试
- [ ] Markdown / JSON 报告含聚合表
- [ ] `--strict-pipeline` CLI
- [ ] `eval/README.md` 更新读报告一节

---

*09-l4-live-probe-spec.md · 波次 D · 2026-06-05*
