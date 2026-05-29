# command — 子 Agent 任务单

主 Agent **只下达目标、约束、验收标准**；具体设计与实现步骤由子 Agent 在约束内自主完成，并在 `feedback/` 中说明方案。

---

## Phase 1 任务

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [PHASE1-OVERVIEW](./PHASE1-OVERVIEW.md) | 总规划、边界、规范（必读） | — |
| [P1-CHANGE-GOVERNANCE](./P1-CHANGE-GOVERNANCE.md) | 实现变更治理 + 测试 | ✅ 已通过 |
| [P1-DOCS](./P1-DOCS.md) | 用户文档 | ✅ 已通过 |
| [P1-REVIEW](./P1-REVIEW.md) | 总验收 | ✅ Phase 1 结项 |

---

## 派发流程

1. 用户在新对话 @ `PHASE1-OVERVIEW` + 具体任务单 + 相关 `struct/`
2. 子 Agent 自行设计方案 → 实现 → 写 `feedback/<TASK_ID>.md`
3. 主 Agent 只按 Done Definition / 契约验收，不审查实现路径

---

## 新任务

复制 [`TEMPLATE.md`](./TEMPLATE.md)。
