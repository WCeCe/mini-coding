# EV-2-GRADING-SCHEMA — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-2-GRADING-SCHEMA
- **状态**: 完成
- **依赖**: EV-1-VERIFY-ALIGN ✅

---

## 方案摘要

### 目标

扩展 `tasks.json` 支持 `tier` / `grading` / `lock_tests`；`run_eval.py` 按 grading 分支终判；迁移现有 5 条任务。

### 设计决策

1. **`resolve_task_grading(task)`** — 显式 `grading` 优先；缺省时：有 `expect_files` → `exact`，仅 `verify` → `tests_only`（向后兼容）。
2. **`check_task_grading(root, task)`** — 统一终判入口：
   - `exact`：lock_tests → expect_files → verify
   - `tests_only`：lock_tests → verify（跳过 expect_files）
3. **`build_fake_outputs`** — `tests_only` 任务若有 `expect_files` 仍反推 patch（`off_by_one_sum`）；无 expect 时仅 Gate。
4. **tasks.json 迁移** — 5 条均为 `tier: easy`；4 条 `grading: exact`；`off_by_one_sum` 为 `grading: tests_only` + `lock_tests: true`。

### 改动文件

| 路径 | 说明 |
|------|------|
| `eval/tasks.json` | 5 条任务迁移 + tier/grading/lock_tests |
| `eval/run_eval.py` | `resolve_task_grading`、`check_task_grading`；`run_single_task` 改用 grading 终判 |
| `eval/README.md` | tier/grading 表、终判顺序、缺省规则 |
| `tests/test_eval_runner.py` | +5 条 grading 分支回归测 |
| `docs/feedback/EV-2-GRADING-SCHEMA.md` | 本回报 |

未改 harness 节点业务逻辑（复用 EV-1 `verify_rules`）。

---

## 验收自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| 5 条均有 `tier: easy` | ✅ | `test_tasks_migrated_tier_and_grading` |
| `off_by_one_sum` tests_only + lock_tests | ✅ | 同上 |
| `tests_only` 无 expect 匹配仅凭 verify pass | ✅ | `test_tests_only_passes_without_expect_match` |
| `exact` 行为与 GL 一致 | ✅ | `test_exact_requires_expect_files_match`、现有 fake 全绿 |
| `--fake` 全绿 | ✅ | 5/5 |
| pytest + ruff | ✅ | 见下方 |

---

## 验证结果

### `python eval/run_eval.py --fake`

```
**合计**：5/5 通过
```

### `python -m pytest tests/test_eval_runner.py -q`

```
14 passed
```

### `python -m ruff check .`

```
All checks passed!
```

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-05 复验：`--fake` 5/5；pytest 186 passed；grading schema 与 tasks 迁移符合契约。
