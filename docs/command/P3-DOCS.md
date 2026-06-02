# 任务单：P3-DOCS

## 元信息

- **TASK_ID**: P3-DOCS
- **TASK_TYPE**: DOCS
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P3-MAKE-PLAN ✅

---

## 目标

在根 [`README.md`](../../README.md) 中补充 **Phase 3 首项**用户说明：`make_plan` 工具用途、plan 在 session/memory 中的行为、CLI `--plan-first` 含义与示例。

---

## 约束

- **仅文档** — 不改 `mini_coding_agent/` 业务逻辑
- 与 [`struct/phase3.md`](../struct/phase3.md)、[`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md) 一致
- 说明 `delegate` vs `make_plan` 分工（一句话即可）
- 不展开 benchmark、后续 Phase 3 未派活项
- 保持 README 现有结构与语气；不重复 struct 全文

---

## 交付物

- 更新 [`README.md`](../../README.md)
- 回报：[`feedback/P3-DOCS.md`](../feedback/P3-DOCS.md)（改了哪些章节、自检清单）

---

## 验收标准

- [ ] README 含 `make_plan` 说明（何时用、参数、输出形状摘要）
- [ ] README 含 `--plan-first` 说明与示例命令
- [ ] README 提及 `/memory` 可查看 plan 摘要
- [ ] 无与实现不符的声称
- [ ] feedback 落盘

---

## 参考资料

- [`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md)
- [`struct/phase3.md`](../struct/phase3.md) §7 面试一句话（可改写为用户向表述）

---

*实现路径由子 Agent 自定*
