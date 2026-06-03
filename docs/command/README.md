# command — 子 Agent 任务单

主 Agent **只下达目标、约束、验收标准**；具体设计由子 Agent 完成。`struct/` 大阶段文档：`phase1.md` … `phase4.md`。

**工程规范**：各 Phase `OVERVIEW` §3 均引用铁律 §7 — 用户可见文案中文，详见 [`struct/04-user-facing-locale.md`](../struct/04-user-facing-locale.md)。

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

## Phase 3 任务（已结项 ✅）

策略：先 coding 链路深度，benchmark 暂缓。struct 见 [`phase3.md`](../struct/phase3.md)。

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [PHASE3-OVERVIEW](./PHASE3-OVERVIEW.md) | 总规划（make_plan 首项） | — |
| [P3-MAKE-PLAN](./P3-MAKE-PLAN.md) | 任务规划工具 + `--plan-first` | ✅ |
| [P3-DOCS](./P3-DOCS.md) | README 用户说明 | ✅ |
| [P3-REVIEW](./P3-REVIEW.md) | Phase 3 首项总验收 | ✅ |

---

## Phase 4 任务（进行中）

struct 见 [`phase4.md`](../struct/phase4.md)。

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [PHASE4-OVERVIEW](./PHASE4-OVERVIEW.md) | 总规划（Skill 加载） | — |
| [P4-SKILLS](./P4-SKILLS.md) | Skill 发现 + 两阶段加载 + `load_skill` + `--skills` | ✅ |
| [P4-DOCS](./P4-DOCS.md) | README § Skills（Phase 4） | ✅ |
| [P4-REVIEW](./P4-REVIEW.md) | Phase 4 总验收 | ✅ |

---

## Agent 重构（非 Phase · 进行中）

`agent.py` 模块拆分 R1→R4。struct 见 [`refactor-agent.md`](../struct/refactor-agent.md)。

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [REFACTOR-OVERVIEW](./REFACTOR-OVERVIEW.md) | 总规划 | — |
| [R1-PROTOCOL-EXTRACT](./R1-PROTOCOL-EXTRACT.md) | `protocol.py` | ✅ |
| [R2-GOVERNANCE-EXTRACT](./R2-GOVERNANCE-EXTRACT.md) | `governance.py` + dead path | ✅ |
| [R3-PROMPT-EXTRACT](./R3-PROMPT-EXTRACT.md) | `prompt.py` | ✅ |
| [R4-TOOLS-EXTRACT](./R4-TOOLS-EXTRACT.md) | `tools/` | ✅ |
| [REFACTOR-REVIEW](./REFACTOR-REVIEW.md) | 总验收 + 02 更新 | ✅ |

> **注释要求**：重构时尽量保留用户既有注释；迁代码时带走；见 OVERVIEW §3。

---

## 新任务

复制 [`TEMPLATE.md`](./TEMPLATE.md)。
