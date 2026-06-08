# struct — 项目构想与阶段记录

主 Agent 维护。每个**大阶段**只保留一份文档；过程细节在 `feedback/`。

---

## 阅读顺序（推荐）

1. [`01-vision-and-roadmap.md`](./01-vision-and-roadmap.md) — 总目标、铁律、Phase 7
2. **[`ARCHITECTURE.md`](./ARCHITECTURE.md)** — **系统总览**（推荐新人第一站）
3. **[`project-architecture-plan.md`](./project-architecture-plan.md)** — 架构整理 Batch 0–8
4. [`phase1.md`](./phase1.md) ~ [`phase5-graph.md`](./phase5-graph.md) — Phase 1–5 ✅
5. **[`phase7.md`](./phase7.md)** — 当前代码迭代（7.1 ✅ · 7.2 ✅ · **7.3 大纲**）
6. [`graph-subsystem.md`](./graph-subsystem.md) · [`platform-subsystem.md`](./platform-subsystem.md) — 子系统深描
7. [`02-codebase-reference.md`](./02-codebase-reference.md) — 模块速查
8. [`docs/eval/README.md`](../eval/README.md) + [`eval/README.md`](../../eval/README.md) — Eval 规格与操作

---

## 阶段文档

| 文件 | 内容 | 状态 |
|------|------|------|
| `phase1.md` | 变更治理 | ✅ |
| `phase2.md` | Hook + 可观测 + YAML | ✅ |
| `phase3.md` | 任务规划 | ✅ |
| `phase4.md` | Skill | ✅ |
| `phase5-graph.md` | Graph 编排 + eval 黄金闭环 | ✅ |
| **`phase7.md`** | Generate 迭代总纲 | 🔄 |
| `phase7.1-generate-fix-bug.md` | 写前策略 + retry 回滚 | ✅ |
| `phase7.2-guided-patch.md` | 系统 old_text + stage_trace + RIG | ✅ |
| `phase7.3-outline.md` | protocol 围栏 + no_file_hint | 📋 大纲 |
| **`project-architecture-plan.md`** | 全项目架构整理分批计划 | Batch 0–6 ✅ |

---

## 状态板

| 项目 | 状态 |
|------|------|
| Phase 1–5 | ✅ |
| Eval 波次 C/D | ✅ 结项（历史见 command/） |
| **架构整理** | Batch 0–6 ✅ |
| **Phase 7.3** | 📋 [`phase7.3-outline.md`](./phase7.3-outline.md) |
| Live Generate 8 条 | **5/8** · [`eval/runs/README.md`](../../eval/runs/README.md) |
| Live 全量 19 条（7.2 后） | **8/19** · [`eval/baselines/`](../eval/baselines/README.md) |

---

## 其它

| 文件 | 用途 |
|------|------|
| [`03-collaboration-model.md`](./03-collaboration-model.md) | 主/子 Agent 分工 |
| [`04-user-facing-locale.md`](./04-user-facing-locale.md) | 用户可见中文规范 |
| [`refactor-agent.md`](./refactor-agent.md) | Agent 模块重构 ✅ |

> 原 Phase 2.1 已并入 `phase2.md`。`command/`、`feedback/` 为历史派活归档，新工作写 struct/phase* 与 eval/QA_LOG。
