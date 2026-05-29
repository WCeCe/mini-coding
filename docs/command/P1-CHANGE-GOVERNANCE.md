# 任务单：P1-CHANGE-GOVERNANCE

## 元信息

- **TASK_ID**: P1-CHANGE-GOVERNANCE
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是

---

## 目标

为 `write_file` / `patch_file` 实现**变更治理层**，达到 [`struct/06`](../struct/06-phase1-portfolio-and-depth.md) §4 Done Definition 中的功能与工程指标。

---

## 约束（必须遵守）

- 见 [`PHASE1-OVERVIEW.md`](./PHASE1-OVERVIEW.md) §3 工程规范
- 见 [`struct/05`](../struct/05-phase1-implementation-design.md) 可靠性契约与架构约束
- 不改模型 tool 协议；不治理 `run_shell`

---

## 交付物

1. 代码：`mini_coding_agent.py`（及必要时的 `tests/`）
2. 回报：[`feedback/P1-CHANGE-GOVERNANCE.md`](../feedback/P1-CHANGE-GOVERNANCE.md)，须包含：
   - **你的方案摘要**（架构、数据存哪、审批与回滚流程——由你设计）
   - **契约对照表**：每条可靠性契约如何满足
   - **Done Definition 自证**：§4.1 / §4.2 逐项说明
   - pytest / ruff 输出

---

## 验收标准

以 [`struct/06` §4](../struct/06-phase1-portfolio-and-depth.md) 为准；主 Agent 不验收「是否采用某种具体实现路径」。

---

## 参考资料

- [`struct/04`](../struct/04-phase1-decisions-and-mvp.md) — 已对齐决策
- [`struct/02`](../struct/02-codebase-reference.md) — 现有架构
- 用户调研：[`my_research/phase_1/`](../my_research/phase_1/)（可选）

---

*主 Agent 下达 · 实现路径由子 Agent 自定*
