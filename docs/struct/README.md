# struct — 项目构想与阶段记录

主 Agent 维护。每个**大阶段**只保留一份文档；过程细节在 `feedback/`。

---

## 阅读顺序

1. [`01-vision-and-roadmap.md`](./01-vision-and-roadmap.md) — 总目标、铁律、路线图
2. [`phase1.md`](./phase1.md) — 变更治理 ✅
3. [`phase2.md`](./phase2.md) — Hook + 可观测 + 重构 ✅
4. [`02-codebase-reference.md`](./02-codebase-reference.md) — 代码架构速查
5. [`03-collaboration-model.md`](./03-collaboration-model.md) — 主/子 Agent 分工

---

## 阶段文档（仅大阶段）

| 文件 | 内容 | 状态 |
|------|------|------|
| `phase1.md` | 变更治理（diff、checkpoint、回滚） | ✅ |
| `phase2.md` | Hook 扩展 + 三层栈 + 包重构 + YAML | ✅ |
| `phase3.md` | （未开工） | — |

> 原 Phase 2.1（终端 trace、shell 审计、YAML）已并入 `phase2.md`，不再单独成阶段。

---

## 状态板

| 项目 | 状态 |
|------|------|
| Phase 1 | ✅ |
| Phase 2（含 Hook 用户价值） | ✅ |
| 测试 | 43 passed, 1 skipped |

*新大阶段：`phase3.md`*
