# command — 子 Agent 任务单

主 Agent **只下达目标、约束、验收标准**；具体设计由子 Agent 完成。`struct/` 大阶段文档：`phase1.md` … `phase5-graph.md`。

**工程规范**：各 Phase `OVERVIEW` §3 均引用铁律 §8 — 用户可见文案中文，详见 [`struct/04-user-facing-locale.md`](../struct/04-user-facing-locale.md)。

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

## Phase 4 任务（已结项 ✅）

struct 见 [`phase4.md`](../struct/phase4.md)。

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [PHASE4-OVERVIEW](./PHASE4-OVERVIEW.md) | 总规划（Skill 加载） | — |
| [P4-SKILLS](./P4-SKILLS.md) | Skill 发现 + 两阶段加载 + `load_skill` + `--skills` | ✅ |
| [P4-DOCS](./P4-DOCS.md) | README § Skills（Phase 4） | ✅ |
| [P4-REVIEW](./P4-REVIEW.md) | Phase 4 总验收 | ✅ |

---

## Phase 5 任务（Graph 编排 · 已结项 ✅）

struct 见 [`phase5-graph.md`](../struct/phase5-graph.md)。含 **波次 A（5.1–5.6 MVP）** 与 **波次 B（GL-1–5 eval 黄金闭环）**。

### 波次 A — Graph MVP（5.1–5.6）

| 子阶段 | TASK_ID | 说明 | 状态 |
|--------|---------|------|------|
| — | [PHASE5-OVERVIEW](./PHASE5-OVERVIEW.md) | 派活索引（历史） | — |
| 5.1 | [P5.1-HARNESS-ENTRY](./P5.1-HARNESS-ENTRY.md) | Gate + runner + open | ✅ |
| 5.2 | [P5.2-TEMPLATES-PLANNER](./P5.2-TEMPLATES-PLANNER.md) | 五模板 + Planner | ✅ |
| 5.3 | [P5.3-FIX-BUG-PIPELINE](./P5.3-FIX-BUG-PIPELINE.md) | 节点 + fix_bug E2E | ✅ |
| 5.4 | [P5.4-RIG](./P5.4-RIG.md) | index 离线图谱 | ✅ |
| 5.5 | [P5.5-FIVE-INTENTS](./P5.5-FIVE-INTENTS.md) | 五类 E2E + executor | ✅ |
| 5.6 | [P5.6-SESSION](./P5.6-SESSION.md) | 会话字段 | ✅ |
| — | [P5-DOCS](./P5-DOCS.md) / [P5-REVIEW](./P5-REVIEW.md) | 文档 / MVP 验收 | ✅ |

### 波次 B — eval 黄金闭环（GL-1–5）

| 顺序 | TASK_ID | 说明 | 状态 |
|------|---------|------|------|
| — | [GOLDEN-LOOP-OVERVIEW](./GOLDEN-LOOP-OVERVIEW.md) | 派活索引（历史） | — |
| 1 | [GL-1-EVAL-INFRA](./GL-1-EVAL-INFRA.md) | eval 框架 | ✅ |
| 2 | [GL-2-LOCATE-SNIPPETS](./GL-2-LOCATE-SNIPPETS.md) | Locate snippet | ✅ |
| 3 | [GL-3-VERIFY-ERROR-FORMAT](./GL-3-VERIFY-ERROR-FORMAT.md) | 错误摘要 | ✅ |
| 4 | [GL-4-FIX-BUG-SLIM](./GL-4-FIX-BUG-SLIM.md) | fix_bug 瘦模板 | ✅ |
| 5 | [GL-5-LIVE-EVAL](./GL-5-LIVE-EVAL.md) | live 基线 | ✅ |
| 6 | [GL-REVIEW](./GL-REVIEW.md) | 总验收 | ✅ |

feedback 索引：[`feedback/README.md`](../feedback/README.md) § Phase 5。

---

## Agent 重构（非 Phase · 已完成 ✅）

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

## Eval 波次 C — 修复与加固（进行中 📋）

struct 见 [`eval-repair-plan.md`](../struct/eval-repair-plan.md)。

| 顺序 | TASK_ID | 说明 | 状态 |
|------|---------|------|------|
| — | [EVAL-REPAIR-OVERVIEW](./EVAL-REPAIR-OVERVIEW.md) | 派活索引 | — |
| 1 | [EV-1-VERIFY-ALIGN](./EV-1-VERIFY-ALIGN.md) | verify 与 eval 对齐 | ⬜ |
| 2 | [EV-2-GRADING-SCHEMA](./EV-2-GRADING-SCHEMA.md) | tier / grading | ⬜ |
| 3 | [EV-3-GENERATE-ROBUST](./EV-3-GENERATE-ROBUST.md) | Generate 鲁棒性 | ⬜ |
| 4 | [EV-4-TASKS-EASY](./EV-4-TASKS-EASY.md) | 简单档 ≥12 条 | ⬜ |
| 5 | [EV-5-TASKS-MEDIUM](./EV-5-TASKS-MEDIUM.md) | 一般档 ≥3 条 | ⬜ |
| 6 | [EV-6-BASELINE-REPORT](./EV-6-BASELINE-REPORT.md) | 基线对比 | ⬜ |
| 7 | [EV-7-DOCS-CI](./EV-7-DOCS-CI.md) | 文档 + CI | ⬜ |
| 8 | [EV-REVIEW](./EV-REVIEW.md) | 总验收 | ⬜ |

---

## UX 优化（非 Phase）

| TASK_ID | 说明 | 状态 |
|---------|------|------|
| [OPT-WAIT-DISPLAY](./OPT-WAIT-DISPLAY.md) | 模型 `complete()` 阻塞期间 stderr 单行 spinner | ✅ 2026-06-03 |
| [OPT-ASK-TIMING](./OPT-ASK-TIMING.md) | 每次 ask 结束 append LLM/tool 耗时 JSONL | ✅ → 由 HOOK-ASK-EVENTS 归位 |
| [HOOK-ASK-EVENTS](./HOOK-ASK-EVENTS.md) | 扩展 ask/llm Hook 触发点 + AskTiming 迁入 hooks/ | ✅ 2026-06-03 |

---

## 新任务

复制 [`TEMPLATE.md`](./TEMPLATE.md)。
