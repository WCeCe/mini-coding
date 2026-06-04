# GL-REVIEW — 黄金闭环总验收

## 元信息

- **TASK_ID**: GL-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P0
- **可以写代码**: 否
- **依赖**: GL-1 ～ GL-5 全部 feedback 已提交

---

## 目标

对照 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §8 Done Definition，独立验收黄金闭环是否结项；更新 struct 状态板；确认冻结清单未被违反。

---

## 约束

- 不派新功能；仅复审与文档状态更新
- 若 GL-5 live 通过率低于 100%，**仍可结项**，但必须满足「≥1 pass + 失败可追溯」

---

## 交付物

- 回报：[`feedback/GL-REVIEW.md`](../feedback/GL-REVIEW.md)
- 更新 [`struct/README.md`](../struct/README.md) 状态板（黄金闭环 ✅）

---

## 验收标准

- [ ] struct/phase5-graph.md §11 全部勾选并附证据
- [ ] GL-1～GL-5 feedback 齐全
- [ ] `python -m pytest -q`、`python -m ruff check .` 通过
- [ ] eval FakeModel 全 task pass
- [ ] 真实 Ollama ≥1 task pass（见 GL-5 报告）
- [ ] 复审确认：Hook / Skill / 非 fix_bug 模板 **无迭代提交**
- [ ] 主 Agent 标记 GOLDEN-LOOP-OVERVIEW 任务状态为 ✅

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md)
- [`GOLDEN-LOOP-OVERVIEW.md`](./GOLDEN-LOOP-OVERVIEW.md)
- 各 `feedback/GL-*.md`
