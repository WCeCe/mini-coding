# EV-2-GRADING-SCHEMA — 任务评分 schema（tier / grading）

## 元信息

- **TASK_ID**: EV-2-GRADING-SCHEMA
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: EV-1-VERIFY-ALIGN

---

## 目标

扩展 `eval/tasks.json` schema，支持 **`tier`**（`easy` | `medium` | `hard`）、**`grading`**（`exact` | `tests_only`）、**`lock_tests`**（bool）；更新 `run_eval.py` 按 grading 终判；迁移现有 5 条任务并更新 `eval/README.md`。

---

## 约束

- 契约：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §3、§5.2
- **向后兼容**：缺省 `grading` 时 — 有 `expect_files` → `exact`；仅 `verify` → `tests_only`
- `build_fake_outputs()` 在 `tests_only` 任务上仍须可推导 Fake 队列（或标记 `fake_skip_expect`）
- 不新增 pip 依赖
- 铁律 §6–§8

---

## 交付物

- `eval/tasks.json` — 5 条迁移 + 字段说明
- `eval/run_eval.py` — `check_task_grading()` 或等价逻辑
- `eval/README.md` — tier / grading 表
- `tests/test_eval_runner.py` — grading 分支覆盖
- 回报：[`feedback/EV-2-GRADING-SCHEMA.md`](../feedback/EV-2-GRADING-SCHEMA.md)

---

## 验收标准

- [ ] 5 条旧任务均有 `tier: easy`；`off_by_one_sum` 为 `grading: tests_only` + `lock_tests: true`
- [ ] `tests_only` 任务在无 `expect_files` 匹配时，仅凭 verify 可 pass
- [ ] `exact` 任务行为与 GL 阶段一致
- [ ] `python eval/run_eval.py --fake` 全绿
- [ ] pytest + ruff 通过

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)
- [`eval/README.md`](../../eval/README.md)
