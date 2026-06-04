# 任务单：P5-DOCS

## 元信息

- **TASK_ID**: P5-DOCS
- **TASK_TYPE**: DOCS
- **优先级**: P0
- **可以写代码**: 否（仅文档；不改业务逻辑）
- **依赖**: P5.5-FIVE-INTENTS ✅（代码行为已冻结）

---

## 目标

在根 [`README.md`](../../README.md) 增加 **§ Graph Harness (Phase 5)**：五类意图、`--harness`、`--gate-log`、`rig build`、open 降级、MVP vs 5.7+ Future 表；更新文首 bullet 与 CLI flags 表。

---

## 约束

- 铁律 §8：用户可见说明 **中文**；CLI 标志、intent_id、JSON 字段 **英文**
- 与 [`struct/phase5-graph.md`](../struct/phase5-graph.md) 一致；**不夸大**未实现能力
- 不删用户既有注释（无代码改动则 N/A）

---

## 交付物

- 更新 `README.md`
- 回报：[`feedback/P5-DOCS.md`](../feedback/P5-DOCS.md)

---

## 验收标准

- [ ] README 有 Graph Harness 专节
- [ ] 五类 intent 表与 struct §5.1 一致
- [ ] 说明 `--harness`、`--gate-log`、`rig build`
- [ ] 明确 low/失败 → open；Phase 1 治理仍适用
- [ ] Future 表列出 5.7+（增量 RIG、混合 Gate 等）

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md)
- [`feedback/P5.5-FIVE-INTENTS.md`](../feedback/P5.5-FIVE-INTENTS.md)

---

*文档任务 · 无 pytest 要求（可选 spell-check）*
