# struct — 项目构想与阶段记录

主 Agent 维护。每个**大阶段**只保留一份文档；过程细节在 `feedback/`。

---

## 阅读顺序

1. [`01-vision-and-roadmap.md`](./01-vision-and-roadmap.md) — 总目标、铁律、路线图
2. [`phase1.md`](./phase1.md) — 变更治理 ✅
3. [`phase2.md`](./phase2.md) — Hook + 可观测 + 重构 ✅
4. [`phase3.md`](./phase3.md) — 任务规划 + coding 链路深度 ✅
5. [`phase4.md`](./phase4.md) — Skill 加载 ✅
6. [`phase5-graph.md`](./phase5-graph.md) — Graph 编排（DAG + Gate + eval 黄金闭环）✅
7. [`eval-repair-plan.md`](./eval-repair-plan.md) — **Eval 波次 C** 修复与加固 ✅
8. [`eval-architecture-plan.md`](./eval-architecture-plan.md) — **Eval 波次 D** 架构体检（文档已就绪）
9. [`eval/README.md`](../eval/README.md) — **Eval 波次 D 展开规格**（五层体系 · schema · 路线图）
10. [`02-codebase-reference.md`](./02-codebase-reference.md) — 代码架构速查
11. [`03-collaboration-model.md`](./03-collaboration-model.md) — 主/子 Agent 分工
12. [`04-user-facing-locale.md`](./04-user-facing-locale.md) — 用户可见文案中文规范（铁律 §8）
13. [`refactor-agent.md`](./refactor-agent.md) — Agent 模块重构（非 Phase）✅

---

## 阶段文档（仅大阶段）

| 文件 | 内容 | 状态 |
|------|------|------|
| `phase1.md` | 变更治理（diff、checkpoint、回滚） | ✅ |
| `phase2.md` | Hook 扩展 + 三层栈 + 包重构 + YAML | ✅ |
| `phase3.md` | 任务规划 + coding 链路深度 | ✅ |
| `phase4.md` | Skill 加载与可扩展工作流 | ✅ |
| `phase5-graph.md` | Graph 编排：Gate、DAG、index、eval 黄金闭环 | ✅ 结项 2026-06-04 |

> 原 Phase 2.1（终端 trace、shell 审计、YAML）已并入 `phase2.md`，不再单独成阶段。  
> 原 `phase5-graph.md` + `phase5-graph.md` 已合并为 `phase5-graph.md`。

---

## 状态板

| 项目 | 状态 |
|------|------|
| Phase 1 | ✅ |
| Phase 2（含 Hook 用户价值） | ✅ |
| Phase 3 | ✅ 已结项（make_plan + docs） |
| Phase 4（Skills + 文档 + REVIEW） | ✅ P4-REVIEW 2026-06-02 |
| benchmark | 暂缓（外部 SWE-bench；内循环见 **Eval 波次 C**） |
| Agent 重构（R1–R4 + REVIEW） | ✅ 2026-06-02 |
| **Phase 5（Graph 编排）** | ✅ **结项**（P5-REVIEW + GL-REVIEW · live 2/5） |
| **Eval 波次 C（EV-1–7）** | ✅ **结项** · [`eval-repair-plan.md`](./eval-repair-plan.md) |
| **Eval 波次 D（架构体检）** | 📋 文档已就绪 · [`eval-architecture-plan.md`](./eval-architecture-plan.md) · [`eval/`](../eval/README.md) |
| 目录结构 platform/modes/index | ✅ 2026-06-04 |
| Hook / Skill / 五类其余意图 live | ⏸ 保留，暂不迭代 |
| 测试 | 167 passed, 1 skipped |
