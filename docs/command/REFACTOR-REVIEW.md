# 任务单：REFACTOR-REVIEW

## 元信息

- **TASK_ID**: REFACTOR-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P1
- **可以写代码**: 否（仅可更新 `02-codebase-reference.md` 文档）
- **依赖**: R4-TOOLS-EXTRACT ✅

---

## 目标

独立复验 **Agent 全量重构（R1–R4）** 是否达到 [`struct/refactor-agent.md`](../struct/refactor-agent.md) Done Definition；更新 [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) 模块 map。

---

## 约束

- 不修改业务逻辑（文档除外）  
- 独立 `pytest -q`、`ruff check .`  
- 对照 R1–R4 feedback 与注释迁移说明 spot-check  

---

## 交付物

- 更新 `struct/02-codebase-reference.md`（仓库布局、模块职责、调用链）  
- [`feedback/REFACTOR-REVIEW.md`](../feedback/REFACTOR-REVIEW.md) — 通过/不通过 + Blocker  

---

## 验收标准

- [ ] struct/refactor-agent §4 Done Definition 逐项有证据  
- [ ] dead path 已清除（write/patch 仅治理链）  
- [ ] agent.py 行数在目标范围或 feedback 解释  
- [ ] pytest / ruff 独立复验通过  
- [ ] 02-codebase-reference 与代码一致  

---

## 参考资料

- [`feedback/R1-PROTOCOL-EXTRACT.md`](../feedback/R1-PROTOCOL-EXTRACT.md) … R4  
- [`struct/refactor-agent.md`](../struct/refactor-agent.md)

---

*主 Agent 下达*
