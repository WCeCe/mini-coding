# L3 架构维度 Bench 规格（B1–B5）

> 返回索引：[`README.md`](./README.md) · Schema：[`03-task-schema.md`](./03-task-schema.md)

五条专项任务，每条验证一个**架构维度**。必须含 `dimension`、`architecture`、`fake_script`，并通过 L2 契约测。

---

## 1. 总览

| ID | task_id（建议） | dimension | tier | 测的架构点 |
|----|-----------------|-----------|------|------------|
| B1 | `bench_retry_off_by_one` | `retry` | medium | verify→generate 重试，2 步 patch |
| B2 | `bench_decoy_calc_backup` | `decoy` | medium | Locate 不被 backup 文件误导 |
| B3 | `bench_gate_explain_boundary` | `gate_boundary` | easy | explain 问句不进 fix_bug DAG |
| B4 | `bench_no_rig_search` | `no_rig` | medium | 无 index.db，search/files_hint 回退 |
| B5 | `import_chain_rate`（升格） | `multi_file` | medium | 改 root cause 非 symptom |

---

## 2. B1：retry

### 2.1 设计意图

验证 executor 在 verify fail 后：

1. 跳回 generate（非直接 pipeline fail）
2. `generate_attempt` 递增
3. 第二次 patch 使用 `last_verify_error` 上下文
4. 不超过 `generate_max_attempts`

### 2.2 任务定义

```json
{
  "id": "bench_retry_off_by_one",
  "tier": "medium",
  "dimension": "retry",
  "grading": "tests_only",
  "lock_tests": true,
  "description": "第一次 patch 故意错误，verify fail 后 retry 成功",
  "message": "pytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3",
  "setup_files": {
    "sum_first.py": "def sum_first(n):\n    s = 0\n    for i in range(1, n):\n        s += i\n    return s\n",
    "tests/test_sum.py": "from sum_first import sum_first\n\ndef test_sum_first():\n    assert sum_first(3) == 6\n"
  },
  "verify": "pytest",
  "harness_intent": "fix_bug",
  "architecture": {
    "intent": "fix_bug",
    "gate": { "route": "harness_pipeline", "confidence": "high" },
    "pipeline_must_succeed": true,
    "no_open_fallback": true,
    "verify": { "method": "pytest" },
    "generate_max_attempts": 2,
    "must_modify": ["sum_first.py"]
  },
  "fake_script": [
    { "gate": { "intent_id": "fix_bug", "confidence": "high" } },
    {
      "patch": {
        "path": "sum_first.py",
        "old_text": "for i in range(1, n):",
        "new_text": "for i in range(1, n - 1):"
      }
    },
    {
      "patch": {
        "path": "sum_first.py",
        "old_text": "for i in range(1, n - 1):",
        "new_text": "for i in range(1, n + 1):"
      }
    }
  ]
}
```

### 2.3 契约断言重点

| 断言 | 期望 |
|------|------|
| stderr 中 generate 出现 2 次 | true |
| 第一次 verify fail | true |
| 第二次 verify ok | true |
| `generate_max_attempts` ≤ 2 | true |
| outcome_ok | true |

---

## 3. B2：decoy

### 3.1 设计意图

工作区存在内容相似的干扰文件 `calc_backup.py`，Locate 与 Generate 必须修改 `calc.py` 而非 backup。

### 3.2 任务定义

```json
{
  "id": "bench_decoy_calc_backup",
  "tier": "medium",
  "dimension": "decoy",
  "grading": "tests_only",
  "lock_tests": true,
  "description": "calc.py 与 calc_backup.py 内容相似，只应修前者",
  "message": "Traceback (most recent call last):\n  File \"calc.py\", line 2, in add\n    return a + c\nNameError: name 'c' is not defined",
  "setup_files": {
    "calc.py": "def add(a, b):\n    return a + c\n",
    "calc_backup.py": "def add(a, b):\n    return a + c\n",
    "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
  },
  "verify": "pytest",
  "harness_intent": "fix_bug",
  "architecture": {
    "intent": "fix_bug",
    "gate": { "route": "harness_pipeline", "confidence": "high" },
    "pipeline_must_succeed": true,
    "locate": { "must_include_files": ["calc.py"] },
    "must_modify": ["calc.py"],
    "must_not_modify": ["calc_backup.py"],
    "must_not_modify_prefixes": ["tests/"]
  },
  "fake_script": [
    { "gate": { "intent_id": "fix_bug", "confidence": "high" } },
    {
      "patch": {
        "path": "calc.py",
        "old_text": "return a + c",
        "new_text": "return a + b"
      }
    }
  ]
}
```

### 3.3 契约断言重点

| 断言 | 期望 |
|------|------|
| must_modify.calc.py | true |
| must_not_modify.calc_backup.py | true |
| locate.must_include.calc.py | true |

---

## 4. B3：gate_boundary

### 4.1 设计意图

用户消息是 **explain** 类问句，Gate 应分类为 `explain` + `harness_pipeline`（explain 模板）或 `route=open`，**不得**进入 fix_bug DAG 改代码。

### 4.2 任务定义

```json
{
  "id": "bench_gate_explain_boundary",
  "tier": "easy",
  "dimension": "gate_boundary",
  "grading": "tests_only",
  "description": "解释代码问句不应触发 fix_bug 改文件",
  "message": "请解释一下 calc.py 里的 add 函数是做什么的，不需要修改任何文件。",
  "setup_files": {
    "calc.py": "def add(a, b):\n    return a + b\n"
  },
  "verify": "none",
  "harness_intent": "fix_bug",
  "architecture": {
    "gate": {
      "intent_id": "explain",
      "confidence": "high",
      "route": "harness_pipeline"
    },
    "pipeline_must_succeed": true,
    "must_modify": [],
    "must_not_modify": ["calc.py"]
  },
  "fake_script": [
    {
      "gate": { "intent_id": "explain", "confidence": "high" }
    },
    {
      "final": "add 函数将两个参数相加并返回。"
    }
  ]
}
```

**注意**：此任务 `harness_intent` 字段仅表示 eval 分类；实际走 **explain** 模板。`must_not_modify.calc.py` 断言磁盘不变。

### 4.3 变体：route=open

若 Gate 对 explain 返回 `route=open`，architecture 可改为：

```json
"gate": { "route": "open", "confidence": "low" },
"pipeline_must_succeed": false
```

FakeModel 只提供 gate 步，后续 open loop 用 final 模拟。

---

## 5. B4：no_rig

### 5.1 设计意图

工作区** deliberately 不运行** `rig build`，无 `index.db`。Locate 必须靠 `files_hint` + `search` 工具产出 snippet。

### 5.2 任务定义

```json
{
  "id": "bench_no_rig_search",
  "tier": "medium",
  "dimension": "no_rig",
  "grading": "exact",
  "description": "无 RIG index，仅靠 traceback 路径 + search 定位",
  "message": "Traceback (most recent call last):\n  File \"helper.py\", line 3, in mul\n    return a * c\nNameError: name 'c' is not defined",
  "setup_files": {
    "helper.py": "def mul(a, b):\n    return a * c\n"
  },
  "expect_files": {
    "helper.py": "def mul(a, b):\n    return a * b\n"
  },
  "verify": "py_compile",
  "harness_intent": "fix_bug",
  "architecture": {
    "intent": "fix_bug",
    "gate": { "route": "harness_pipeline", "confidence": "high" },
    "pipeline_must_succeed": true,
    "locate": {
      "must_include_files": ["helper.py"],
      "min_snippets_with_source_lines": 1
    },
    "must_modify": ["helper.py"]
  },
  "fake_script": [
    { "gate": { "intent_id": "fix_bug", "confidence": "high" } },
    {
      "patch": {
        "path": "helper.py",
        "old_text": "return a * c",
        "new_text": "return a * b"
      }
    }
  ]
}
```

### 5.3 测试 setup 要求

```python
# test_eval_contract.py 或 conftest
# 确保 tmp_path 下无 index/ 或 index.db
assert not (root / "index.db").exists()
```

### 5.4 P2-b 联动

启用 Locate snippet 门槛后，B4 若 snippet 为空应 `locate fail`，契约测验证此行为。

---

## 6. B5：multi_file（升格 import_chain_rate）

### 6.1 设计意图

Bug 在 `rates.py`，pytest 失败栈或用户描述指向 `app.py`。必须修改 **root cause** 文件。

### 6.2 对现有任务的增补

在 `eval/tasks.json` 的 `import_chain_rate` 上增加：

```json
{
  "dimension": "multi_file",
  "architecture": {
    "intent": "fix_bug",
    "gate": { "route": "harness_pipeline", "confidence": "high" },
    "pipeline_must_succeed": true,
    "no_open_fallback": true,
    "locate": { "must_include_files": ["rates.py"] },
    "verify": { "method": "pytest" },
    "must_modify": ["rates.py"],
    "must_not_modify_prefixes": ["tests/"]
  },
  "fake_script": [
    { "gate": { "intent_id": "fix_bug", "confidence": "high" } },
    {
      "patch": {
        "path": "rates.py",
        "old_text": "return base * rate",
        "new_text": "return base * rate / 100"
      }
    }
  ]
}
```

（`old_text`/`new_text` 须与当前 `setup_files` 中 rates.py 实际内容一致，实现时核对。）

### 6.3 Live 预期

medium 任务 live 允许 0/N；报告应能区分 `locate_wrong_file`（改了 app.py）vs `verify_pytest`（改了 rates 但逻辑仍错）。

---

## 7. 入库检查清单

每条 B1–B5 入库前：

- [ ] `id` 唯一
- [ ] `dimension` 标签正确
- [ ] `architecture` 字段完整
- [ ] `fake_script` 与 setup 内容一致（patch old_text 能 unique match）
- [ ] `test_eval_contract.py` 单条 parametrized pass
- [ ] 不与现有 easy 任务 duplicate（除 B5 升格）

---

## 8. Live 可选跑法

```bash
python eval/run_eval.py --task bench_retry_off_by_one
python eval/run_eval.py --report json | jq '.tasks[] | select(.failure_type) | .task_id'
```

L3 live **不要求全过**；按 `failure_type` 聚合即可。

---

*08-l3-arch-bench-spec.md · 波次 D · 2026-06-05*
