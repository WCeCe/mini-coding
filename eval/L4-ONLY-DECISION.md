# L2 契约 vs L4-only 任务划分（Batch 5 决策）

> **日期**：2026-06-08 · **状态**：已采纳 · 扩展契约见架构计划 Batch 8（可选）

---

## 背景

`eval/tasks.json` 共 **19 条**。其中 **7 条** 含 `architecture` + `fake_script`，由 `tests/test_eval_contract.py` 做 L2/L3 管线契约断言；其余 **12 条** 历史上仅用于 L4 live 能力探针。

Batch 5 需决定：是否为剩余 12 条补 `architecture`，或明确标注 **L4-only**。

---

## 决策

**采纳 L4-only 标注（文档层），暂不扩 task_schema 字段。**

| 类别 | 数量 | 说明 |
|------|------|------|
| **L2/L3 契约任务** | 7 | 已有 `architecture` + `fake_script`；CI 必绿 |
| **L4-only 任务** | 12 | 仅 `message` + setup + grading；**不**要求 `pipeline_ok` 契约断言 |

**理由**：

1. 7 条已覆盖 Gate、retry、decoy、gate_boundary、no_rig、multi_file、lock_tests 等架构维度（B1–B5 + P0-b）。
2. 其余 12 条多为 easy bugfix 探针；补 `fake_script` 工作量大，收益重复（Batch 8 可选）。
3. L4 live 仍跑全部 19 条；`pipeline_ok` 仅对含 `architecture` 的任务计算（现有 `run_eval.py` 行为不变）。

---

## 任务清单

### L2/L3 契约（7 条）

| task_id | dimension / 备注 |
|---------|------------------|
| `nameerror_calc` | P0-b：traceback + py_compile |
| `off_by_one_sum` | P0-b：pytest + lock_tests |
| `bench_retry_off_by_one` | B1 retry |
| `bench_decoy_calc_backup` | B2 decoy |
| `bench_gate_explain_boundary` | B3 gate_boundary |
| `bench_no_rig_search` | B4 no_rig |
| `import_chain_rate` | B5 multi_file |

### L4-only（12 条）

| task_id | tier | 主要探针 |
|---------|------|-----------|
| `syntaxerror_paren` | easy | generate protocol / patch |
| `nameerror_greet` | easy | generate protocol |
| `wrong_operator_calc` | easy | 简单 patch |
| `importerror_sqrt` | easy | import 修复 |
| `missing_return_abs` | easy | Generate 专项（7.2 pass） |
| `wrong_comparison_max` | easy | 逻辑修复 |
| `syntaxerror_colon` | easy | 语法修复 |
| `nameerror_index` | easy | NameError |
| `off_by_one_range` | easy | off-by-one |
| `empty_body_double` | easy | 空函数体 |
| `no_file_hint_add` | medium | slots/locate 无 hint |
| `logic_median_even` | medium | Generate 专项（7.2 pass） |

---

## 后续（Batch 8 可选）

- 为 Generate 专项 8 条中尚无契约者补最小 `architecture` + `fake_script`；或
- 在 `task_schema.py` 增加显式 `"eval_layers": ["L4"]` 字段。

在此之前，文档与报告以本文件为 **L4-only 单一真相源**。
