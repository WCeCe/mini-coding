# EV-1-VERIFY-ALIGN — Harness verify 与 eval 终判对齐

## 元信息

- **TASK_ID**: EV-1-VERIFY-ALIGN
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: 无（波次 C 第一步）

---

## 目标

消除 harness `verify` 节点与 `eval/run_eval.py` 终判的 **双标准**：当任务含测试套件时，harness 内必须通过 **pytest（或任务指定的 test_command）** 才算 verify 成功；禁止「仅 py_compile 通过即报 ok」导致的假阳性。对含 `tests/` 的任务，agent **不得修改测试文件**（`lock_tests` 基础行为，可与 EV-2 字段合并落地）。

---

## 约束

- 契约：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §5.1
- 不新增 pip 依赖
- 改码范围：`mini_coding_agent/modes/graph/nodes/verify.py`、`eval/run_eval.py`（仅终判与 harness 对齐部分）、相关 pytest
- 不修改 Gate、Locate、Generate 业务（除 verify 调用链）
- 铁律 §6–§8

---

## 交付物

- `mini_coding_agent/modes/graph/nodes/verify.py` — 行为修正
- `tests/test_harness_verify_align.py`（或扩展现有 harness 测）— 含「错误逻辑 + py_compile 过 + pytest 应 fail」
- `eval/run_eval.py` — 终判与 harness 规则一致（若需抽取共用函数，放在 eval 或 graph 内最小模块）
- 回报：[`feedback/EV-1-VERIFY-ALIGN.md`](../feedback/EV-1-VERIFY-ALIGN.md)

---

## 验收标准

- [ ] 工作区有 `tests/` 时，harness `verify` 执行 pytest，不以单独 py_compile 替代
- [ ] 回归：`off_by_one_sum` 在 **错误修复** 时 harness `verify` 为 **fail**（非仅 expect_files fail）
- [ ] 测试文件被 patch 时 verify 或 post_check **fail**
- [ ] `python eval/run_eval.py --fake` 仍全绿（或文档说明需 EV-2 后迁移任务）
- [ ] `python -m pytest -q`、`python -m ruff check .` 通过
- [ ] 全量 pytest 不低于派活前基线

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)
- [`feedback/GL-5-LIVE-EVAL.md`](../feedback/GL-5-LIVE-EVAL.md) — `off_by_one_sum` 案例
- [`nodes/verify.py`](../../mini_coding_agent/modes/graph/nodes/verify.py)
- [`slots.py`](../../mini_coding_agent/modes/graph/slots.py) — `detect_test_command`
