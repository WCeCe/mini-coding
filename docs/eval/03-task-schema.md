# tasks.json 与 architecture 契约 Schema

> 返回索引：[`README.md`](./README.md) · L2 规格：[`07-l2-contract-spec.md`](./07-l2-contract-spec.md)

---

## 1. 文件位置

```
eval/tasks.json          # 当前：15 条 fix_bug 任务（JSON 数组）
eval/task_schema.py      # 规划：解析/校验函数（P0-b 实现）
```

未来若任务过多，可拆为 `eval/tasks/easy.json` + `eval/tasks/arch/` 目录，schema 不变。

---

## 2. 基础字段（波次 C，已实现）

每条任务必须包含：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 唯一标识，用于 `--task` 与基线对比 |
| `tier` | `"easy"` \| `"medium"` \| `"hard"` | ✅ | 难度分档 |
| `grading` | `"exact"` \| `"tests_only"` | ✅ | 终判模式 |
| `message` | string | ✅ | 用户输入（模拟 CLI 提问） |
| `setup_files` | object | ✅ | 相对路径 → 文件内容，写入临时工作区 |
| `verify` | `"pytest"` \| `"py_compile"` \| `"none"` | ✅ | 终判 verify 方式 |
| `harness_intent` | string | ✅ | 当前仅 `"fix_bug"` |
| `description` | string | 推荐 | 人类可读场景标签 |

### 2.1 可选字段（波次 C）

| 字段 | 类型 | 说明 |
|------|------|------|
| `expect_files` | object | `grading=exact` 时字节级期望；`tests_only` 时可作文档参考 |
| `lock_tests` | boolean | 默认：setup 含 `tests/` 时为 true；禁止 agent 改测试 |

### 2.2 grading 缺省规则

```python
def resolve_task_grading(task: dict) -> str:
    if task.get("grading"):
        return task["grading"]
    if task.get("expect_files"):
        return "exact"
    return "tests_only"
```

### 2.3 tier 定义

| tier | 定义 | 示例 |
|------|------|------|
| `easy` | 单文件；消息含路径或 traceback；≤1 行逻辑修复 | `nameerror_calc` |
| `medium` | 多文件 **或** 消息不点名文件；需符号/RIG | `no_file_hint_add`, `import_chain_rate` |
| `hard` | 5+ 文件；跨模块；多步推理 | 占位，波次 D 不强制 |

---

## 3. 波次 D 扩展字段

### 3.1 `dimension`（L3 架构 bench）

| 值 | 含义 |
|----|------|
| `retry` | verify→generate 重试 |
| `decoy` | Locate 干扰文件 |
| `gate_boundary` | Gate 边界（不误入 fix_bug） |
| `no_rig` | 无 index.db 回退 |
| `multi_file` | 跨文件 root cause |
| （缺省） | 普通能力任务，非架构专项 |

### 3.2 `architecture`（管线契约）

向后兼容：**缺省 `architecture` 的旧任务**仅跑 grading 终判，不断言 `pipeline_ok`。

```json
{
  "architecture": {
    "intent": "fix_bug",
    "gate": {
      "route": "harness_pipeline",
      "confidence": "high",
      "intent_id": "fix_bug"
    },
    "pipeline_must_succeed": true,
    "no_open_fallback": true,
    "locate": {
      "must_include_files": ["rates.py"],
      "min_snippets_with_source_lines": 1
    },
    "verify": {
      "method": "pytest"
    },
    "generate_max_attempts": 2,
    "must_modify": ["rates.py"],
    "must_not_modify": ["calc_backup.py"],
    "must_not_modify_prefixes": ["tests/"]
  }
}
```

#### 3.2.1 字段详解

| 字段 | 类型 | 说明 | 断言时机 |
|------|------|------|----------|
| `intent` | string | 预期 DAG 模板 | Planner 加载后 |
| `gate.route` | string | 预期 `session.last_gate.route` | handle_ask 后 |
| `gate.confidence` | string | 预期 confidence | 同上 |
| `gate.intent_id` | string | 预期 intent（B3 可为非 fix_bug） | 同上 |
| `pipeline_must_succeed` | boolean | `PipelineResult.ok` | executor 返回后 |
| `no_open_fallback` | boolean | stderr 不得含「降级 open」 | handle_ask 后 |
| `locate.must_include_files` | string[] | locate 输出或 `last_files_touched` 须含 | pipeline 后 |
| `locate.min_snippets_with_source_lines` | int | locate 节点 snippet 质量（L2 mock 可测） | locate 节点后 |
| `verify.method` | `"pytest"` \| `"py_compile"` \| `"lock_tests"` | `session.last_verify.method` 映射 | pipeline 后 |
| `generate_max_attempts` | int | generate 调用次数上限（含 retry） | stderr 计数 |
| `must_modify` | string[] | 相对 setup 内容有变更的文件 | 终判前 diff |
| `must_not_modify` | string[] | 内容不得变的文件 | 终判前 diff |
| `must_not_modify_prefixes` | string[] | 路径前缀不得变（如 `tests/`） | lock_tests 逻辑 |

#### 3.2.2 verify.method 与 session.last_verify 映射

| architecture.verify.method | session.last_verify.method |
|----------------------------|----------------------------|
| `pytest` | `shell` |
| `py_compile` | `py_compile` |
| `lock_tests` | （lock 失败时 verify 不 ok） |

### 3.3 `fake_script`（仅 L2/L3，FakeModel 队列）

**不改变 live 行为**；仅 `FakeModelClient` + `test_eval_contract.py` 使用。

```json
{
  "fake_script": [
    {
      "gate": {
        "intent_id": "fix_bug",
        "confidence": "high"
      }
    },
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

#### 3.3.1 fake_script 步骤类型

| 类型 | JSON 形状 | 模拟的 LLM 响应 |
|------|-----------|-----------------|
| Gate | `{ "gate": { "intent_id", "confidence", "skill"? } }` | Gate 一次 completion |
| Patch | `{ "patch": { "path", "old_text", "new_text" } }` | generate 返回 `patch_file` tool |
| Write | `{ "write": { "path", "content" } }` | generate 返回 `write_file` tool |
| Final | `{ "final": "..." }` | generate/review 返回 final（用于测失败） |
| Raw | `{ "raw": "..." }` | 原样作为 model 输出 |

#### 3.3.2 retry 场景的多步 patch

B1 `retry` 维度示例：

```json
{
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
  ],
  "architecture": {
    "generate_max_attempts": 2,
    "pipeline_must_succeed": true
  }
}
```

第一次 patch 故意错误 → verify fail → retry → 第二次 patch 正确。

#### 3.3.3 gate_boundary（B3）示例

```json
{
  "fake_script": [
    {
      "gate": {
        "intent_id": "explain",
        "confidence": "high"
      }
    }
  ],
  "architecture": {
    "gate": {
      "intent_id": "explain",
      "route": "open",
      "confidence": "high"
    },
    "pipeline_must_succeed": false,
    "no_open_fallback": false
  }
}
```

注意：B3 测的是 **Gate 不误入 fix_bug**；`pipeline_must_succeed: false` 表示不应进入 fix_bug DAG。

---

## 4. 完整示例：nameerror_calc（P0-b 首批）

```json
{
  "id": "nameerror_calc",
  "tier": "easy",
  "grading": "exact",
  "description": "traceback 含 calc.py，NameError 修复为 a+b",
  "message": "Traceback (most recent call last):\n  File \"calc.py\", line 2, in add\n    return a + c\nNameError: name 'c' is not defined",
  "setup_files": {
    "calc.py": "def add(a, b):\n    return a + c\n"
  },
  "expect_files": {
    "calc.py": "def add(a, b):\n    return a + b\n"
  },
  "verify": "py_compile",
  "harness_intent": "fix_bug",
  "architecture": {
    "intent": "fix_bug",
    "gate": {
      "route": "harness_pipeline",
      "confidence": "high",
      "intent_id": "fix_bug"
    },
    "pipeline_must_succeed": true,
    "no_open_fallback": true,
    "locate": {
      "must_include_files": ["calc.py"],
      "min_snippets_with_source_lines": 1
    },
    "verify": {
      "method": "py_compile"
    },
    "generate_max_attempts": 1,
    "must_modify": ["calc.py"],
    "must_not_modify_prefixes": ["tests/"]
  },
  "fake_script": [
    {
      "gate": {
        "intent_id": "fix_bug",
        "confidence": "high"
      }
    },
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

---

## 5. 完整示例：off_by_one_sum（verify 对齐）

```json
{
  "id": "off_by_one_sum",
  "tier": "easy",
  "grading": "tests_only",
  "lock_tests": true,
  "architecture": {
    "intent": "fix_bug",
    "gate": { "route": "harness_pipeline", "confidence": "high" },
    "pipeline_must_succeed": true,
    "no_open_fallback": true,
    "verify": { "method": "pytest" },
    "must_modify": ["sum_first.py"],
    "must_not_modify_prefixes": ["tests/"]
  },
  "fake_script": [
    { "gate": { "intent_id": "fix_bug", "confidence": "high" } },
    {
      "patch": {
        "path": "sum_first.py",
        "old_text": "for i in range(1, n):",
        "new_text": "for i in range(1, n + 1):"
      }
    }
  ]
}
```

**关键契约**：harness verify 必须跑 pytest，不得以 py_compile 假阳性通过（EV-1 回归）。

---

## 6. 校验函数（规划：eval/task_schema.py）

```python
VALID_TIERS = frozenset({"easy", "medium", "hard"})
VALID_GRADINGS = frozenset({"exact", "tests_only"})
VALID_DIMENSIONS = frozenset({
    "retry", "decoy", "gate_boundary", "no_rig", "multi_file",
})
VALID_VERIFY_METHODS = frozenset({"pytest", "py_compile", "lock_tests", "none"})


def validate_task(task: dict) -> list[str]:
    """返回校验错误列表；空列表表示合法。"""
    errors: list[str] = []
    # ... 必填字段、类型、architecture 子字段 ...
    return errors


def load_tasks(path: Path) -> list[dict]:
    tasks = json.loads(path.read_text(encoding="utf-8"))
    for task in tasks:
        errs = validate_task(task)
        if errs:
            raise ValueError(f"task {task.get('id')}: {errs}")
    return tasks


def tasks_with_fake_script(tasks: list[dict]) -> list[dict]:
    return [t for t in tasks if t.get("fake_script")]
```

---

## 7. 迁移计划：现有 15 条任务

| 阶段 | 任务 | 动作 |
|------|------|------|
| P0-b | `nameerror_calc`, `off_by_one_sum`, `import_chain_rate` | 补全 `architecture` + `fake_script` |
| P1-b | B1–B4 | 新增 4 条 + dimension |
| P1-b | `import_chain_rate` | 加 `dimension: multi_file`，升格 B5 |
| P2 | 其余 easy 11 条 | 逐步补 architecture（优先级低于 B1–B5） |

缺 `architecture` 的任务：**不影响**现有 L4 live 行为；L2 契约测跳过。

---

## 8. 与终判的关系

```
handle_ask 返回
  → assert_pipeline_contract(task, agent, stderr)   # architecture 字段
  → check_task_grading(root, task)                   # grading / lock / verify
  → pipeline_ok = contract.all_passed
  → outcome_ok = grading_err is None
  → passed = f(outcome_ok, pipeline_ok, strict, fallback)
```

两套正交：可以 `pipeline_ok=True, outcome_ok=False`（管线对但 patch 内容错）。

---

*03-task-schema.md · 波次 D · 2026-06-05*
