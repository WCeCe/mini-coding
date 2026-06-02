# command — 子 Agent 任务单

主 Agent **只下达目标、约束、验收标准**；具体设计由子 Agent 完成。`struct/` 仅保留大阶段文档：`phase1.md`、`phase2.md`、`phase3.md`。

---

## Phase 1 任务（已完成）

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [PHASE1-OVERVIEW](./PHASE1-OVERVIEW.md) | 总规划 | — |
| [P1-CHANGE-GOVERNANCE](./P1-CHANGE-GOVERNANCE.md) | 变更治理 | ✅ |
| [P1-DOCS](./P1-DOCS.md) | 文档 | ✅ |
| [P1-REVIEW](./P1-REVIEW.md) | 总验收 | ✅ |

## Phase 2 任务（已完成）

Phase 2 分两次派活，同属一个大阶段；struct 见 [`phase2.md`](../struct/phase2.md)。

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [PHASE2-OVERVIEW](./PHASE2-OVERVIEW.md) | 总规划（Hook + 重构） | — |
| [P2-HOOK-AND-REFACTOR](./P2-HOOK-AND-REFACTOR.md) | Hook + 包重构 | ✅ |
| [P2-DOCS](./P2-DOCS.md) / [P2-REVIEW](./P2-REVIEW.md) | 文档 / 验收 | ✅ |
| [P2.1-HOOK-USER-VALUE](./P2.1-HOOK-USER-VALUE.md) | 三层栈 + YAML（Phase 2 续） | ✅ |
| [P2.1-DOCS](./P2.1-DOCS.md) / [P2.1-REVIEW](./P2.1-REVIEW.md) | 文档 / 验收 | ✅ |

> `PHASE2.1-OVERVIEW.md` 为历史派活记录，内容已并入 `struct/phase2.md`。

---

## 新任务

复制 [`TEMPLATE.md`](./TEMPLATE.md)。Phase 3 起新建 `phase3.md` + `command/PHASE3-*`。
