# 任务单：P5-REVIEW

## 元信息

- **TASK_ID**: P5-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P0
- **可以写代码**: 否（仅允许修文档/测试若发现阻断性小问题须在 feedback 列出；大改退回派活）
- **依赖**: P5.1–P5.6 feedback ✅ · P5-DOCS ✅

---

## 目标

独立复验 **Phase 5 MVP** 是否满足 [`struct/phase5-graph.md`](../struct/phase5-graph.md) **§8 Done Definition**；spot-check README；跑全量 pytest + ruff。

---

## 约束

- 不擅自扩大 scope；不替子 Agent 重写 Harness
- 发现问题分类：**阻断** / **建议** / **文档不一致**

---

## 交付物

- 回报：[`feedback/P5-REVIEW.md`](../feedback/P5-REVIEW.md)
- 若通过：建议主 Agent 更新 `struct/README.md` 状态板 Phase 5 → ✅

---

## 验收标准（对照 struct §11）

- [ ] `--harness on`：五类意图各 ≥1 E2E pytest 存在且通过（审查 tests 与 feedback）
- [ ] Gate：FakeModel 测试；非法/low → open
- [ ] `rig build` + locate 使用图谱
- [ ] generate 走 governance
- [ ] README MVP vs Future 与实现一致
- [ ] `python -m pytest -q` 全文记录在回报
- [ ] `python -m ruff check .` 通过
- [ ] 无第六类 intent、无 chromadb/tree-sitter 偷渡依赖

---

## 参考资料

- 全部 `feedback/P5.*.md`
- [`PHASE5-OVERVIEW.md`](./PHASE5-OVERVIEW.md)

---

*验收任务*
