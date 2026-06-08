# EV-4-TASKS-EASY — 任务集扩展·简单档

## 元信息

- **TASK_ID**: EV-4-TASKS-EASY
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P1
- **可以写代码**: 是
- **依赖**: EV-2-GRADING-SCHEMA

---

## 目标

将 **easy** 档 `fix_bug` 任务从 5 条扩至 **≥12 条**，覆盖：NameError、SyntaxError、ImportError、运算符/比较符、简单 off-by-one、空 body / 缺 return 等；均标注 `tier: easy`。保持 `--fake` 全绿。

---

## 约束

- 契约：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §3
- 单任务仍保持：单文件为主、消息可含路径/traceback
- 不重复现有 5 条 id
- 新任务须有 `description`；grading 按 EV-2 约定
- 不新增 pip 依赖

---

## 交付物

- `eval/tasks.json`（或 `eval/tasks/easy/*.json` 若已支持目录加载 — 由子 Agent 定，须在 README 说明）
- `tests/test_eval_runner.py` — 抽样或全量 fake pass
- `eval/README.md` — 任务表更新
- 回报：[`feedback/EV-4-TASKS-EASY.md`](../feedback/EV-4-TASKS-EASY.md)

---

## 验收标准

- [ ] easy 档 ≥12 条
- [ ] `python eval/run_eval.py --fake` 全绿
- [ ] 每条任务有唯一 `id` 与 `tier: easy`
- [ ] pytest + ruff 通过

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)
- 现有 [`eval/tasks.json`](../../eval/tasks.json)
