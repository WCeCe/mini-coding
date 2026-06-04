# GL-3-VERIFY-ERROR-FORMAT — Verify 错误摘要

## 元信息

- **TASK_ID**: GL-3-VERIFY-ERROR-FORMAT
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: GL-1-EVAL-INFRA 验收通过（可与 GL-2 并行）

---

## 目标

实现 `format_error_for_model()`：将 verify 失败时的 py_compile / pytest / shell 长输出压缩为 3–8 行关键信息，写入 `ctx.last_verify_error`，供 Generate retry prompt 使用。

---

## 约束

- 契约见 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-3
- 摘要上限建议 ≤800 字符；无法解析时 `clip` 原文
- 仅改 harness 包内逻辑（`error_format.py`、`executor.py`；Generate 已读 `last_verify_error` 则不必大改）
- 不修改 Hook / Skill
- 铁律 §6–§8

---

## 交付物

- `mini_coding_agent/harness/error_format.py`（推荐独立模块）
- `mini_coding_agent/harness/executor.py` — verify 失败处调用格式化
- `tests/test_harness_error_format.py`
- 回报：[`feedback/GL-3-VERIFY-ERROR-FORMAT.md`](../feedback/GL-3-VERIFY-ERROR-FORMAT.md)

---

## 验收标准

- [ ] 单测：长 pytest traceback → 摘要含错误类型 + 文件 + 行号
- [ ] 单测：py_compile 错误 → 摘要可读
- [ ] `test_verify_retry_runs_generate_twice` 仍绿；第二次 prompt **不含** 未截断的巨型 log
- [ ] ruff + 全量 pytest 通过

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-3
- [`harness/executor.py`](../../mini_coding_agent/harness/executor.py)
- [`harness/nodes/verify.py`](../../mini_coding_agent/harness/nodes/verify.py)
