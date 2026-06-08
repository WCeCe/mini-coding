# Phase 7.1 — fix_bug Generate 加固（写前策略 + retry 回滚）

> **状态**：✅ 已实现（代码 + 回归测试）  
> **前置**：Phase 5 Graph 编排 ✅ · Eval 波次 C/D 文档 ✅ · L4 live 探针基线（7/19）  
> **关联**：[`phase7.md`](./phase7.md) · [`phase5-graph.md`](./phase5-graph.md) §6 · live 基线 [`eval/runs/live/2026-06-08_full-19tasks.json`](../../eval/runs/live/2026-06-08_full-19tasks.json)

---

## 1. 背景与动机

### 1.1 从 L4 live 发现的问题

对 [`eval/runs/live/2026-06-08_full-19tasks.json`](../../eval/runs/live/2026-06-08_full-19tasks.json)（19 条 Ollama live）按五层体系归因后，**Generate 节点**是 fix_bug 路径的主要瓶颈：

| failure 模式 | 条数 | 典型 task_id |
|--------------|------|--------------|
| 模型 patch `tests/` 而非源码 | 5 | `off_by_one_sum`, `import_chain_rate`, `logic_median_even` |
| patch 格式 / old_text 匹配 | 2+ | `syntaxerror_paren`, `nameerror_greet` |
| verify 通过但 exact 终判失败 | 2 | `wrong_comparison_max`, `nameerror_index` |

其中 **「改 tests/」** 占带 `tests/` 任务失败的大头。eval 终判有 `lock_tests`，**没有任何任务因改 tests 而通过**；问题是模型频繁尝试改 tests，导致 harness verify fail，且 **retry 在已污染的 workspace 上无法恢复**。

### 1.2 与 Phase 1 治理的关系

| 层次 | 职责 | 本 Phase 是否新增 |
|------|------|-------------------|
| **Phase 1 governance** | 写盘安全：checkpoint、diff、原子写、写失败回滚 | 否，复用 |
| **fix_bug 写前策略** | 能不能改、改哪里（禁止 `tests/`） | ✅ 7.1 新增 |
| **verify lock_tests** | 写后对比 tests 快照 | 否，已有 |
| **retry workspace 恢复** | verify / policy fail 后恢复磁盘再 generate | ✅ 7.1 新增 |

**结论**：不是缺少 governance，而是 **governance 只管「怎么安全写」，不管 fix_bug「该不该改 tests」**；且 **checkpoint 已落盘，但未接到 verify→generate retry 路径**。

### 1.3 eval 任务中的「源码」与 `tests/`

每个 eval 任务在临时工作区写入 `setup_files`，构成模拟用户项目：

```
工作区/
├── sum_first.py          ← 源码（bug 在这里，应改这里）
└── tests/test_sum.py     ← 测试（验收标准，lock_tests 禁止修改）
```

`tests/` 暴露的是**期望行为**（如 `assert sum_first(3) == 6`），不是实现答案；改 assert 属于作弊，由 `lock_tests` 拦截。

---

## 2. 阶段目标

| # | 目标 | 状态 |
|---|------|------|
| G1 | fix_bug 下 **写前**禁止 `write_file` / `patch_file` 目标路径为 `tests/` | ✅ |
| G2 | policy 拦截 **不落盘**，错误信息进入 retry prompt | ✅ |
| G3 | verify fail 跳回 generate **前**回滚 workspace（checkpoint + test_baseline） | ✅ |
| G4 | 整理 `generate.py` 结构（解析 / 校验 / prompt 分离） | ✅ |
| G5 | 回归测试（FakeModel，无 Ollama） | ✅ |

**非目标（7.1 不做）**：

- 影子 workspace（验过再写主目录）—— 后续 Phase 7.x 可选
- `grading=exact` + `verify=py_compile` 语义对齐 —— 见 EV-1 / verify 专项
- 全量 L4 live 重跑与基线更新 —— 手动触发

---

## 3. 设计：三层防护

```
模型输出 tool
    │
    ▼
┌─────────────────────────────────────┐
│ ① 写前策略（generate._prepare_tool_args） │
│    fix_bug + path ∈ tests/ → policy_block │
│    不调用 run_tool，磁盘不变              │
└─────────────────────────────────────┘
    │ 通过
    ▼
┌─────────────────────────────────────┐
│ ② 既有链路：validate_tool → governance   │
│    checkpoint 保存改前内容 → 写盘         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ ③ verify（lock_tests / pytest / py_compile）│
└─────────────────────────────────────┘
    │ fail 且 retry 余额
    ▼
┌─────────────────────────────────────┐
│ ④ retry 前恢复（executor）               │
│    restore_checkpoint（上次 patch）      │
│    restore_tests_from_baseline          │
└─────────────────────────────────────┘
    │
    └──► 跳回 generate（prompt 含「上次失败」摘要）
```

### 3.1 为何仍是「先写再 verify」

pytest / py_compile 需要磁盘上已有改过的文件才能跑。**7.1 不改为「验过再写」**，而是：

- **写前**：拦明显非法目标（tests/）
- **写后**：verify 判定
- **retry 前**：回滚，避免错误 patch 累积

与 SWE-bench 等真实基准一致：测试定义「修好了」的契约，hidden gold patch 仅用于评分；模型可见的是 issue + 代码 + 失败日志，不是标准答案源码。

---

## 4. 实现摘要

### 4.1 模块与职责

| 文件 | 变更 |
|------|------|
| `modes/graph/nodes/generate.py` | 主流程拆分；`_prepare_tool_args` 写前策略；prompt 禁止改 tests |
| `modes/graph/verify_rules.py` | `check_fix_bug_must_not_touch_tests`；`restore_tests_from_baseline`；`restore_workspace_for_retry` |
| `modes/graph/executor.py` | generate 成功后记录 checkpoint；policy_block / verify fail 时 retry + 回滚 |
| `modes/graph/types.py` | `HarnessContext.last_generate_checkpoint` |

### 4.2 generate 节点流程

```python
run_generate:
  complete → _parse_tool_call → _prepare_tool_args → run_tool → NodeResult
```

`_prepare_tool_args` 顺序：

1. `patch_file` → `_normalize_patch_args_for_fix_bug`（old_text 对齐，GL-5 已有）
2. `check_fix_bug_must_not_touch_tests(intent_id, path)` → 命中则 `policy_block: True`

policy 失败返回示例：

```
fix_bug 禁止修改测试文件：tests/test_sum.py；请 patch 定位上下文中的源码文件
```

### 4.3 executor retry 语义

与 `fix_bug.json` 中 `retry.verify.max: 2` **共用计数**：

| 触发条件 | 写盘？ | retry 前动作 |
|----------|--------|--------------|
| `policy_block`（写前拦 tests） | 否 | 无回滚；`last_verify_error` ← 策略错误 |
| verify fail（lock_tests / pytest 等） | 是（上一轮） | `restore_workspace_for_retry` |

`restore_workspace_for_retry`：

1. `governance.restore_checkpoint(last_generate_checkpoint)` — 撤销上次成功 patch 的文件
2. `restore_tests_from_baseline(test_baseline)` — 恢复流水线启动时 `tests/` 快照，删除误增测试文件

`test_baseline` 在 `execute_dag` 入口由 `collect_tests_snapshot(root)` 采集，与 verify 节点共用同一规则。

### 4.4 与 open 降级的关系（历史）

7.1 时期 policy / verify 重试耗尽后会 **降级 open**。**Phase 7.2 已取消**；见 [`phase7.2-guided-patch.md`](./phase7.2-guided-patch.md)。

---

## 5. 行为对比

### 5.1 误改 tests（off_by_one_sum 类）

**7.1 之前：**

```
generate patch tests/test_sum.py → 落盘
verify lock_tests fail
retry generate → tests 已脏 → 永久 fail
```

**7.1 之后（理想路径 — 写前拦截）：**

```
generate 目标 tests/ → policy_block，不落盘
retry generate → prompt 含禁止改 tests 提示
patch sum_first.py → verify pass
```

**7.1 之后（兜底 — 仍写入了 tests）：**

```
generate patch tests → 落盘（模型绕过了策略或历史行为）
verify fail → restore checkpoint + baseline
retry → 干净 workspace → 改源码
```

### 5.2 改错源码但 pytest fail

```
generate patch sum_first.py（仍错）→ verify pytest fail
restore checkpoint → sum_first.py 回到改前
retry generate → 在原始 bug 状态上再试
```

---

## 6. 测试

| 测试文件 | 用例 | 覆盖点 |
|----------|------|--------|
| `tests/test_generate_robust.py` | `test_generate_fix_bug_blocks_tests_path_before_run_tool` | 写前拦截，`run_tool` 未调用 |
| `tests/test_harness_verify_align.py` | `test_verify_retry_restores_tests_after_wrong_test_patch` | verify fail 后 baseline 恢复 + retry 成功 |
| `tests/test_harness_verify_align.py` | `test_generate_policy_block_retries_without_writing_tests` | policy_block retry + 第二次改源码 |
| `tests/test_harness_verify_align.py` | `test_restore_tests_from_baseline` | 快照恢复单元行为 |

```bash
python -m pytest tests/test_generate_robust.py \
                 tests/test_harness_verify_align.py \
                 tests/test_harness_fix_bug_e2e.py \
                 tests/test_eval_contract.py -q
```

---

## 7. 验收与后续

### 7.1 Done Definition

- [x] fix_bug generate 写前拒绝 `tests/` 路径
- [x] policy_block 可 retry，错误进入 prompt
- [x] verify fail retry 前 checkpoint + test_baseline 回滚
- [x] `generate.py` 结构整理，行为不变
- [x] 上述 pytest 绿
- [ ] L4 live 重跑并对比基线（手动，不阻塞 CI）

### 7.4 与 open 降级的关系（历史）

7.1 编写时 pipeline 失败会降级 open。**Phase 7.2 已取消该降级**；policy / verify 重试耗尽后直接返回 `流水线失败：…`。见 [`phase7.2-guided-patch.md`](./phase7.2-guided-patch.md)。

### 7.5 建议后续

| 项 | 说明 |
|----|------|
| 引导 patch | ✅ 见 [`phase7.2-guided-patch.md`](./phase7.2-guided-patch.md) |
| protocol 围栏 | 📋 Phase 7.3 |
| 影子 workspace | 可选，低优先级 |

---

## 8. 层间定位（Eval 五层）

| 层 | 7.1 关系 |
|----|----------|
| L1 | 可为 `check_fix_bug_must_not_touch_tests` 补 diagnostic 纯函数用例 |
| L2 | `test_eval_contract` 中 off_by_one_sum / bench_retry 应继续绿 |
| L4 | 预期 lock_tests 类 live 失败减少；需重跑确认 |
| L5 | 若 live 仍有新模式，写入 `docs/eval/QA_LOG.md` |

---

*phase7.1-generate-fix-bug.md · Phase 7 首个子阶段 · 2026-06-08*
