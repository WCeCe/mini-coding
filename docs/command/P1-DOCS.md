# 任务单：P1-DOCS

## 元信息

- **TASK_ID**: P1-DOCS
- **TASK_TYPE**: DOCS
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P1-CHANGE-GOVERNANCE 验收通过

---

## 目标

更新用户面向文档，使他人能理解变更治理能力与**已知限制**，不夸大未实现功能。

---

## 约束

- 与真实实现一致
- 必须写明 Phase 1 **不做**的事（如 run_shell 回滚、一键撤销等）

---

## 交付物

- `README.md`（必须）：Change Governance 小节
- `EXAMPLE.md`（可选）：简短交叉引用
- [`feedback/P1-DOCS.md`](../feedback/P1-DOCS.md)

---

## 验收标准

- [ ] 满足 [`struct/06` §4.2](../struct/06-phase1-portfolio-and-depth.md) README 相关项
- [ ] 无虚假功能描述

---

*主 Agent 下达*
