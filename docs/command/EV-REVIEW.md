# EV-REVIEW — Eval 波次 C 总验收

## 元信息

- **TASK_ID**: EV-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P0
- **可以写代码**: 否
- **依赖**: EV-1 ～ EV-7 全部 feedback 主 Agent 通过

---

## 目标

对照 [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §7 Done Definition，验收波次 C 交付；更新 struct 状态为结项或列未清项；归档 live 基线表。

---

## 约束

- 主 Agent 或用户执行；子 Agent 仅可辅助整理 feedback 索引
- 须复跑 `python eval/run_eval.py --fake` 与全量 pytest

---

## 交付物

- [`feedback/EV-REVIEW.md`](../feedback/EV-REVIEW.md)
- 更新 `struct/eval-repair-plan.md` 状态、`struct/README.md` 状态板

---

## 验收标准

- [ ] §7 Done Definition 全勾选或明确豁免
- [ ] EV-1～7 feedback 均已复审
- [ ] live 基线表已更新（允许 &lt;5/5）
- [ ] 无 scope 外改动未记录

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)
- [`EVAL-REPAIR-OVERVIEW.md`](./EVAL-REPAIR-OVERVIEW.md)
