# struct — 项目构想与阶段记录

主 Agent 维护。每个**大阶段**只保留一份文档；过程细节在 `feedback/`。

---

## 阅读顺序

1. [`01-vision-and-roadmap.md`](./01-vision-and-roadmap.md) — 总目标、铁律、路线图
2. [`phase1.md`](./phase1.md) — 变更治理 ✅
3. [`phase2.md`](./phase2.md) — Hook + 可观测 + 重构 ✅
4. [`phase3.md`](./phase3.md) — 任务规划 + coding 链路深度 ✅
5. [`phase4.md`](./phase4.md) — Skill 加载 🚧（P4-SKILLS 待派活）
6. [`02-codebase-reference.md`](./02-codebase-reference.md) — 代码架构速查
7. [`03-collaboration-model.md`](./03-collaboration-model.md) — 主/子 Agent 分工
8. [`04-user-facing-locale.md`](./04-user-facing-locale.md) — 用户可见文案中文规范（铁律 §7）

---

## 阶段文档（仅大阶段）

| 文件 | 内容 | 状态 |
|------|------|------|
| `phase1.md` | 变更治理（diff、checkpoint、回滚） | ✅ |
| `phase2.md` | Hook 扩展 + 三层栈 + 包重构 + YAML | ✅ |
| `phase3.md` | 任务规划 + coding 链路深度 | ✅ |
| `phase4.md` | Skill 加载与可扩展工作流 | ✅ |

> 原 Phase 2.1（终端 trace、shell 审计、YAML）已并入 `phase2.md`，不再单独成阶段。

---

## 状态板

| 项目 | 状态 |
|------|------|
| Phase 1 | ✅ |
| Phase 2（含 Hook 用户价值） | ✅ |
| Phase 3 | ✅ 已结项（make_plan + docs） |
| Phase 4（Skills + 文档 + REVIEW） | ✅ P4-REVIEW 2026-06-02 |
| 测试 | 66 passed, 1 skipped |
| benchmark | 暂缓（设计稳后再量化） |
