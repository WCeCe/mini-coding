# 任务单：P2-REVIEW

## 元信息

- **TASK_ID**: P2-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P2-HOOK-AND-REFACTOR、P2-DOCS 已完成

---

## 目标

对照 [`struct/07-phase2-portfolio-and-depth.md`](../struct/07-phase2-portfolio-and-depth.md) §4 Done Definition 与 [`struct/07-phase2-reliability-contract.md`](../struct/07-phase2-reliability-contract.md)，独立复验 Phase 2 是否可结项。

---

## 约束

- 不修改业务代码（发现问题写入回报，交主 Agent 裁决）
- 独立运行 `python -m pytest -q` 与 `python -m ruff check .`
- 对照 Phase 1 Done Definition  spot-check（治理相关测试仍绿）

---

## 交付物

- 回报：[`feedback/P2-REVIEW.md`](../feedback/P2-REVIEW.md)
- 结论：**通过** / **不通过**（含 Blocker 列表）

---

## 验收标准

- [ ] §4.1 功能指标逐项有证据（测试名 / 代码路径 / session 样例）
- [ ] §4.2 工程指标逐项有证据
- [ ] §4.3 文档指标逐项有证据
- [ ] 可靠性契约 §3 表格逐项核对
- [ ] 明确 Phase 2 可否结项

---

## 参考资料

- [`feedback/P2-HOOK-AND-REFACTOR.md`](../feedback/P2-HOOK-AND-REFACTOR.md)
- [`feedback/P2-DOCS.md`](../feedback/P2-DOCS.md)
- [`feedback/P1-REVIEW.md`](../feedback/P1-REVIEW.md)（Phase 1 验收格式参考）

---

*主 Agent 下达*
