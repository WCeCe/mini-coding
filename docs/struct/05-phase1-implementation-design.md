# Phase 1 需求与可靠性契约

> **定位**：主 Agent 下达的**需求与约束**，不是实现说明书。  
> **谁补全设计**：子 Agent 在 `feedback/` 中说明自己的方案，并在约束内实现。

**决策摘要**：见 [`04-phase1-decisions-and-mvp.md`](./04-phase1-decisions-and-mvp.md)  
**作品集目标**：见 [`06-phase1-portfolio-and-depth.md`](./06-phase1-portfolio-and-depth.md)

---

## 1. 已对齐决策

| # | 决策 | 选定 |
|---|------|------|
| 1 | 变更预览 | 终端展示 unified diff |
| 2 | 回滚粒度 | 单次 `write_file` / `patch_file` tool |
| 3 | Git 集成 | 只读；文件变更审批前刷新状态并提示风险 |
| 4 | 工具演进 | 保留现有工具名与模型协议，在执行层外包治理 |

---

## 2. 要交付的能力（What）

对 `write_file` 与 `patch_file`：

1. **先预览、后落盘**：用户审批时应看到变更的 diff，而非裸参数
2. **可恢复**：单次 tool 具备 checkpoint；写盘失败可回滚
3. **可审计**：session 能追溯改了什么（至少 diff 摘要、是否回滚）
4. **Git 感知**：脏工作区在审批时有风险提示（不执行 commit）

`run_shell` 与其它工具：**行为与 Phase 1 前一致**。

---

## 3. 可靠性契约（必须满足）

| 场景 | 要求 |
|------|------|
| 用户拒绝审批 | 磁盘与调用前一致 |
| 写盘失败 | 自动回滚到本 tool 的 checkpoint |
| 新建文件后回滚 | 文件应被移除 |
| 修改已有文件后回滚 | 内容恢复为改前 |
| checkpoint 无法建立 | 不得写盘 |
| 回滚时文件已被外部修改 | 明确报错或跳过，不得静默覆盖 |

**不在本阶段保证**：`run_shell` 的文件副作用；一次用户请求内多步修改的一键撤销。

---

## 4. 架构约束（How far, not How to）

- 治理逻辑插在**工具执行层**（如 `run_tool` 一带），**不改**模型输出的 tool 格式与 `parse` 行为
- 主实现仍在 `mini_coding_agent.py` 单文件内
- 不新增运行时 pip 依赖（标准库 + 现有 pytest）
- checkpoint 持久化在 `.mini-coding-agent/` 下（具体结构由子 Agent 设计）

---

## 5. 非目标（本阶段不做）

见 [`04-phase1-decisions-and-mvp.md`](./04-phase1-decisions-and-mvp.md) 与 [`06`](./06-phase1-portfolio-and-depth.md) §3。

---

## 6. 验收归属

**唯一完成标准**：[`06-phase1-portfolio-and-depth.md`](./06-phase1-portfolio-and-depth.md) §4 Done Definition。

子 Agent 在 `feedback/` 中须说明：其方案如何满足 §3 契约与 §4 Done Definition。

---

*struct/05 · 需求契约 · 主 Agent 维护*
