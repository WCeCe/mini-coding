# Phase 1：已对齐决策与 MVP

> 用户确认日期：2026-05-29  
> 实现设计：[`05-phase1-implementation-design.md`](./05-phase1-implementation-design.md)

---

## 1. 背景

当前 `write_file` / `patch_file` 在 `approve` 通过后**直接写盘**，缺少 diff 预览、checkpoint、回滚。Phase 1 补齐**变更治理层**。

---

## 2. 四个决策（已选）

### 决策 1：变更预览放在哪里？

| 选项 | 说明 |
|------|------|
| A. 终端打印 diff | ✅ **已选** |
| B. 写入 session / history | |
| C. Web UI | |

### 决策 2：回滚粒度？

| 选项 | 说明 |
|------|------|
| A. 单次 tool 调用 | ✅ **已选** |
| B. 单次用户请求 | |
| C. 整个 session | |

### 决策 3：Git 集成深度？

| 选项 | 说明 |
|------|------|
| A. 只读 diff / status | ✅ **已选**（risky 前刷新 status 并警告） |
| B. 半自动 commit | |
| C. 全自动 commit | |

### 决策 4：现有工具如何演进？

| 选项 | 说明 |
|------|------|
| A. 保留 write/patch，外层包治理 | ✅ **已选** |
| B. 新 apply_patch，旧工具 deprecated | |
| C. 只保留 unified diff 一种 | |

---

## 3. MVP 范围

### 纳入

- [ ] 修改前自动生成 unified diff
- [ ] 审批时展示 diff（非原始 content / old_text）
- [ ] 每次 write/patch 前 checkpoint
- [ ] 拒绝或失败可回滚
- [ ] session 记录 diff 摘要、checkpoint id、是否回滚

### 推迟到 Phase 2+

- Docker / shell 沙箱
- 多模型、流式
- SWE-bench
- 大目录拆包
- Web UI
- 自动 `git commit`

---

## 4. 下一步

1. 子 Agent 执行 [`command/P1-CHANGE-GOVERNANCE.md`](../command/P1-CHANGE-GOVERNANCE.md)
2. 通过后 → `P1-DOCS` → `P1-REVIEW`
3. 作品集叙述见 [`06-phase1-portfolio-and-depth.md`](./06-phase1-portfolio-and-depth.md)

---

*struct/04 · 决策变更时由主 Agent 更新*
