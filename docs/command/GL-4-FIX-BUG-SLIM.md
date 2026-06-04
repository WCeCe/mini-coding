# GL-4-FIX-BUG-SLIM — fix_bug 模板瘦身

## 元信息

- **TASK_ID**: GL-4-FIX-BUG-SLIM
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: GL-1-EVAL-INFRA 验收通过（可与 GL-2/3 并行）

---

## 目标

黄金闭环的 `fix_bug` 路径在 **verify 通过后即返回成功**，不强制再调 **review** LLM（减少格式失败点与延迟）。保留 `review.py` 供其他意图使用。

---

## 约束

- 契约见 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-4
- 推荐方案：调整 `fix_bug.json` 去掉 review 节点；`executor._resolve_final` 在无 review 时返回明确中文成功文案
- 若改模板，须同步 `tests/test_harness_fix_bug_e2e.py` 的 FakeModel 输出队列（少一次 review mock）
- **不删除** `harness/nodes/review.py`
- 不修改 explain / project_ops / refactor / generate_code 模板
- 铁律 §6–§8

---

## 交付物

- `mini_coding_agent/harness/templates/fix_bug.json`
- `mini_coding_agent/harness/executor.py`（`_resolve_final` 若需调整）
- 更新相关 pytest
- 回报：[`feedback/GL-4-FIX-BUG-SLIM.md`](../feedback/GL-4-FIX-BUG-SLIM.md)

---

## 验收标准

- [ ] fix_bug FakeModel E2E：Gate + Generate [+ retry] 即可完成，**无需** review mock
- [ ] verify 通过后返回非空 `final_text`（中文，含验证通过信息）
- [ ] 其他意图 E2E（若有 review）不受影响
- [ ] ruff + 全量 pytest 通过

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md) §2.1、§7.2 GL-4
- [`harness/templates/fix_bug.json`](../../mini_coding_agent/harness/templates/fix_bug.json)
- [`tests/test_harness_fix_bug_e2e.py`](../../tests/test_harness_fix_bug_e2e.py)
