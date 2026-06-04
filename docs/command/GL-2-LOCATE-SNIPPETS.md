# GL-2-LOCATE-SNIPPETS — Locate 代码片段加固

## 元信息

- **TASK_ID**: GL-2-LOCATE-SNIPPETS
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: GL-1-EVAL-INFRA 验收通过

---

## 目标

确保 `fix_bug` 流水线中 Locate 节点的 `snippets` **始终包含可读的源码正文**（带行号），而不仅是 `# rig: symbol @ file:10` 元数据。Generate 节点禁止再调 read/search，必须仅依赖 Locate 上下文。

---

## 约束

- 契约见 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-2
- **Locate 不得引入 LLM**
- 无 `rig.db` 时必须回退 search + read_file（已有行为保留）
- 可读行范围建议：命中行 ±10，或 RIG `lineno`/`end_lineno`；单 snippet 不宜超过 ~120 行
- 不修改 Hook / Skill / 其他意图模板
- 铁律 §6–§8

---

## 交付物

- `mini_coding_agent/harness/nodes/locate.py`（可新增 `harness/snippet.py`）
- `tests/test_harness_locate_snippets.py`（或并入 `test_rig.py`）
- 回报：[`feedback/GL-2-LOCATE-SNIPPETS.md`](../feedback/GL-2-LOCATE-SNIPPETS.md)

---

## 验收标准

- [ ] 无 rig.db + 仅 `symbols_hint`：snippets 含 `file` 源码行（非空 metadata）
- [ ] 有 rig.db + symbol 命中：snippets 含命中行附近 **代码正文**
- [ ] traceback 含 `files_hint` 时行为不退化（现有 E2E 仍绿）
- [ ] `tests/test_harness_fix_bug_e2e.py`、`tests/test_rig.py` 仍绿
- [ ] GL-1 eval FakeModel 仍 pass（若 GL-1 已合并）
- [ ] ruff + 全量 pytest 通过

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-2
- [`harness/nodes/locate.py`](../../mini_coding_agent/harness/nodes/locate.py)
- [`harness/nodes/generate.py`](../../mini_coding_agent/harness/nodes/generate.py)
- [`rig/query.py`](../../mini_coding_agent/rig/query.py)
