# 任务单：P2-HOOK-AND-REFACTOR

## 元信息

- **TASK_ID**: P2-HOOK-AND-REFACTOR
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是

---

## 目标

1. 实现**一套**工具边界 Hook（`pre_tool` / `post_tool`，只观察），含进程内注册 API  
2. 交付**一个**内置参考 Hook（trace / log：步序、工具名、耗时、成败）  
3. 对代码做**有目的的结构化重构**，且 **Phase 1 全部能力与 pytest 回归不退化**

达到 [`struct/07-phase2-portfolio-and-depth.md`](../struct/07-phase2-portfolio-and-depth.md) §4 功能与工程指标。

---

## 约束（必须遵守）

- 见 [`PHASE2-OVERVIEW.md`](./PHASE2-OVERVIEW.md) §3 工程规范
- 见 [`struct/07-phase2-reliability-contract.md`](../struct/07-phase2-reliability-contract.md) 可靠性契约
- Hook **不得**阻断或修改 tool 执行结果；**不得**绕过 `approve()` / 变更治理
- Hook 异常须 **fail-open**
- 不改模型 tool 协议；不变更 Phase 1 治理语义
- 重构须服务于 Hook 接入与可维护性（非无测试的空搬家）

---

## 交付物

1. 代码：重构后的 Agent 实现 + `tests/`（含 Hook 新测；Phase 1 测全绿）
2. 回报：[`feedback/P2-HOOK-AND-REFACTOR.md`](../feedback/P2-HOOK-AND-REFACTOR.md)，须包含：
   - **方案摘要**（Hook 架构、调用链、内置 Hook 行为）
   - **模块 map**（重构前后文件职责）
   - **契约对照表**：[`07-phase2-reliability-contract.md`](../struct/07-phase2-reliability-contract.md) 每条如何满足
   - **Done Definition 自证**：§4.1 / §4.2 逐项说明
   - **Phase 1 回归说明**：哪些测试证明治理未退化
   - pytest / ruff 输出

---

## 验收标准

以 [`struct/07` §4](../struct/07-phase2-portfolio-and-depth.md) 为准；主 Agent 不验收「是否采用某种具体模块划分或类名」。

---

## 参考资料

- [`struct/07-phase2-decisions-and-mvp.md`](../struct/07-phase2-decisions-and-mvp.md) — 已对齐决策
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) — 现有架构（重构后可在 feedback 更新）
- [`struct/05-phase1-implementation-design.md`](../struct/05-phase1-implementation-design.md) — Phase 1 契约（须继续满足）
- Phase 1 回报：[`feedback/P1-CHANGE-GOVERNANCE.md`](../feedback/P1-CHANGE-GOVERNANCE.md)（可选）

---

*主 Agent 下达 · 实现路径由子 Agent 自定*
