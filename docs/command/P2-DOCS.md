# 任务单：P2-DOCS

## 元信息

- **TASK_ID**: P2-DOCS
- **TASK_TYPE**: DOCS
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P2-HOOK-AND-REFACTOR 已通过主 Agent 验收

---

## 目标

更新 [`README.md`](../../README.md)，使 Phase 2 Hook 与重构后的使用方式对用户可读，达到 [`struct/07-phase2-portfolio-and-depth.md`](../struct/07-phase2-portfolio-and-depth.md) §4.2 文档指标。

---

## 约束

- 只改文档（`README.md`；若模块入口变化可更新运行示例）
- 不修改 `mini_coding_agent.py` 或业务逻辑
- 与 [`struct/07-phase2-reliability-contract.md`](../struct/07-phase2-reliability-contract.md) 一致
- 保留 Phase 1 **Change Governance** 章节；新增 **Extension & Observability**（或等价标题）
- 说明已知限制（如 Hook 只观察、不阻断；无外部脚本 Hook）

---

## 交付物

- 更新后的 `README.md`
- 回报：[`feedback/P2-DOCS.md`](../feedback/P2-DOCS.md)

---

## 验收标准

- [ ] README 有 Extension & Observability：Hook 是什么、默认 trace、如何注册自定义 Hook（概念级，非逐步教程）
- [ ] 若 CLI / 模块路径因重构变化，运行示例已更新
- [ ] Phase 1 Change Governance 与 Known limitations 仍完整
- [ ] Phase 2 已知限制已列出

---

## 参考资料

- [`feedback/P2-HOOK-AND-REFACTOR.md`](../feedback/P2-HOOK-AND-REFACTOR.md)
- [`struct/07-phase2-portfolio-and-depth.md`](../struct/07-phase2-portfolio-and-depth.md) §6 面试叙述（可提炼为用户向说明）

---

*主 Agent 下达*
