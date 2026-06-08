# failure_type 失败分类体系

> 返回索引：[`README.md`](./README.md) · Live 报告：[`09-l4-live-probe-spec.md`](./09-l4-live-probe-spec.md)

Live eval（L4）与契约 eval（L2）共用的 **`failure_type`** 字符串枚举，用于 E2E 分因、基线对比、QA_LOG 记录。设计参考 KWCode GapDetector 11 类型，精简为本仓库 fix_bug 路径所需的 **14 类型**（含 2 个成功标记）。

---

## 1. 与 failure_step 的区别

| 字段 | 粒度 | 来源 | 用途 |
|------|------|------|------|
| `failure_step` | 管线**阶段**（gate/locate/generate/verify/…） | 现有 `infer_failure_step()` | 快速定位大环节 |
| `failure_type` | **根因类型**（可跨 step） | 新 `infer_failure_type()` | 聚合统计、指向具体文件 |

示例：`failure_step=generate`，`failure_type=generate_patch_match` → 应改 `nodes/generate.py` 的 patch 对齐逻辑。

---

## 2. 完整枚举

| `failure_type` | 含义 | 典型触发条件 | 建议优先改动 |
|----------------|------|--------------|--------------|
| `gate_low` | Gate 低置信或未进 pipeline | `confidence=low` 或 `route=open`（任务期望 harness） | `gate.py` / `gate_prompt.py` |
| `gate_wrong_intent` | 意图分类错误 | `last_gate.intent_id` ≠ 任务期望 | `gate.py` |
| `locate_no_snippet` | 无有效源码 snippet | locate 输出无 `# file:N` 行号片段 | `locate.py` / `slots.py` |
| `locate_wrong_file` | 改错文件 | `must_modify` 未变 / 改了 decoy 文件 | `locate.py` / `index/` |
| `generate_protocol` | 未返回合法 tool | stderr 含 `generate 须返回 tool` | `protocol.py` |
| `generate_patch_match` | patch old_text 匹配失败 | `old_text 恰好出现 1 次，实际出现 0 次` | `nodes/generate.py` |
| `generate_governance` | 治理拒绝写文件 | `run_tool` 返回治理错误 | `governance.py` |
| `verify_py_compile` | py_compile 失败 | 语法仍错 | generate / verify |
| `verify_pytest` | pytest 失败 | 逻辑仍错 | generate / verify retry |
| `verify_lock_tests` | 测试被篡改 | lock_tests 快照不一致 | `verify_rules.py` |
| `fallback_open` | 流水线失败且 open 降级 | stderr 含 `降级 open` | `runner.py` + 上游节点 |
| `expect_files` | exact grading 终判不符 | `内容与期望不符` | 任务设计 / generate |
| `exception` | 未捕获异常 | handle_ask 抛错 | 调用栈 |
| `outcome_ok` | 终判通过（结果维） | grading 通过 | — |
| `pipeline_ok` | 契约全满足（管线维） | architecture 断言全过 | — |
| `unknown` | 无法归类 | 以上均不匹配 | 补 taxonomy / 日志 |

---

## 3. 推断顺序（实现规范）

`infer_failure_type(session, stderr, grading_err, task) -> str` 必须**按此顺序**判断，先匹配先返回：

### Step 1：异常

```python
if exception_occurred:
    return "exception"
```

### Step 2：session.last_gate（架构契约任务）

```python
gate = session.get("last_gate") or {}
arch_gate = (task.get("architecture") or {}).get("gate")

if arch_gate:
    if gate.get("route") == "open" or gate.get("confidence") == "low":
        return "gate_low"
    if arch_gate.get("intent_id") and gate.get("intent_id") != arch_gate["intent_id"]:
        return "gate_wrong_intent"
```

非 architecture 任务：若 stderr 含 `route=open` 且 message 明显是 fix_bug → `gate_low`。

### Step 3：open fallback

```python
if "降级 open" in stderr:
    return "fallback_open"
```

### Step 4：终判错误（grading）

按 `grading_err` 文本：

| 关键词 | failure_type |
|--------|--------------|
| `内容与期望不符` / `缺少期望文件` | `expect_files` |
| `测试文件` / `禁止修改测试` | `verify_lock_tests` |
| `pytest` | `verify_pytest` |
| `py_compile` | `verify_py_compile` |

### Step 5：stderr 节点失败（细粒度）

| stderr 模式 | failure_type |
|-------------|--------------|
| `generate 须返回 tool` | `generate_protocol` |
| `old_text 恰好出现` + `实际出现 0` | `generate_patch_match` |
| `old_text 恰好出现` + `实际出现 [2-9]` | `generate_patch_match` |
| `治理` / `checkpoint` / `approval` 拒绝 | `generate_governance` |
| `locate：无有效源码 snippet` | `locate_no_snippet` |
| `locate fail` | `locate_no_snippet`（或 locate_wrong_file，若有 must_modify 上下文） |
| `verify fail` + pytest 上下文 | `verify_pytest` |
| `verify fail` + py_compile 上下文 | `verify_py_compile` |

### Step 6：must_modify 契约（pipeline 后 diff）

```python
if arch.get("must_modify"):
    changed = diff_changed_files(workspace, task["setup_files"])
    if not all(f in changed for f in arch["must_modify"]):
        return "locate_wrong_file"  # 或 generate 未改对文件
```

### Step 7：成功标记

```python
if outcome_ok and pipeline_ok:
    return "pipeline_ok"  # 或报告层同时标 outcome_ok
if outcome_ok:
    return "outcome_ok"  # pipeline 有问题但结果对
```

### Step 8：回退

```python
return "unknown"
```

---

## 4. failure_step 映射表（兼容现有）

| failure_type | 默认 failure_step |
|--------------|-------------------|
| `gate_low`, `gate_wrong_intent` | `gate` |
| `locate_no_snippet`, `locate_wrong_file` | `locate` |
| `generate_protocol`, `generate_patch_match`, `generate_governance` | `generate` |
| `verify_py_compile`, `verify_pytest`, `verify_lock_tests` | `verify` |
| `fallback_open` | `pipeline` |
| `expect_files` | `expect_files` |
| `exception` | `exception` |

实现时：`failure_step` 可由 `failure_type` 派生，或保持现有 `infer_failure_step()` 与之并行。

---

## 5. 聚合报告格式

Markdown 报告尾部（L4）：

```markdown
## 架构痛点聚合（failure_type）

| failure_type | 数量 | 任务 |
|--------------|------|------|
| generate_patch_match | 5 | syntaxerror_paren, nameerror_greet, … |
| locate_wrong_file | 2 | import_chain_rate, no_file_hint_add |
| gate_low | 1 | logic_median_even |

## 建议优先改动

1. `mini_coding_agent/modes/graph/nodes/generate.py` — 5 条 patch 匹配失败
2. `mini_coding_agent/modes/graph/nodes/locate.py` — 2 条定位错误
3. `mini_coding_agent/modes/graph/gate.py` — 1 条 Gate 低置信
```

JSON 报告 `summary.failure_types`：

```json
{
  "summary": {
    "passed": 2,
    "total": 15,
    "failure_types": {
      "generate_patch_match": 5,
      "locate_wrong_file": 2,
      "verify_pytest": 3
    }
  }
}
```

---

## 6. GL-5 已知失败映射（历史基线）

| task_id | 原 failure_step | 映射 failure_type | 根因 |
|---------|-----------------|-------------------|------|
| nameerror_calc | — | `pipeline_ok` | 通过 |
| syntaxerror_paren | expect_files | `generate_patch_match` | old_text 0 匹配 |
| nameerror_greet | expect_files | `generate_protocol` | tool 解析失败 |
| off_by_one_sum | expect_files | `verify_pytest` 或 generate 内容错 | patch 逻辑偏 |
| wrong_operator_calc | — | `pipeline_ok` | 通过 |

写入 [`QA_LOG.md`](./QA_LOG.md) 轮次 0。

---

## 7. 测试要求

`tests/test_eval_runner.py` 须覆盖（P0-a，无 Ollama）：

| 用例 | 输入 | 期望 failure_type |
|------|------|-------------------|
| mock session route=open | arch 期望 harness | `gate_low` |
| stderr patch 0 match | — | `generate_patch_match` |
| grading pytest err | — | `verify_pytest` |
| stderr 降级 open | — | `fallback_open` |
| must_modify 未满足 | diff | `locate_wrong_file` |

---

*04-failure-taxonomy.md · 波次 D · 2026-06-05*
