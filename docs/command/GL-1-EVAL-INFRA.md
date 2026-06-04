# GL-1-EVAL-INFRA — Eval 基础设施

## 元信息

- **TASK_ID**: GL-1-EVAL-INFRA
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: 无（黄金闭环第一步）

---

## 目标

建立可重复的 eval 框架：读取 `eval/tasks.json`，在隔离临时仓库中调用 `handle_ask(..., harness_enabled=True)`，断言文件结果与 verify，输出 pass/fail 报告。支持 **FakeModel** 模式（CI/单测）与后续 **--live** 扩展位。

---

## 约束

- 契约见 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-1、§6
- **不修改** Hook、Skill、Gate、Locate、Generate、Verify 业务逻辑（仅调用现有 API）
- 不新增 pip 依赖
- Agent 构建：`approval_policy=auto`、`enable_trace_hook=False`（减少噪声）
- FakeModel 模式下 Gate/Generate 输出由 eval runner 按 task 注入或预设队列
- 铁律 §6–§8

---

## 交付物

- `eval/tasks.json` — 至少 1 个 `nameerror_calc` 任务
- `eval/run_eval.py` — CLI（建议：`--fake`、`--task`、`--report markdown`）
- `eval/README.md` — 用法与字段说明
- `tests/test_eval_runner.py` — FakeModel 下框架自测
- 回报：[`feedback/GL-1-EVAL-INFRA.md`](../feedback/GL-1-EVAL-INFRA.md)

---

## 验收标准

- [ ] `python -m pytest tests/test_eval_runner.py -q` 全绿
- [ ] `python eval/run_eval.py --fake`（或文档等价命令）对 tasks.json 中 1 task **pass**
- [ ] 报告含：task_id、pass/fail、失败原因（若有）
- [ ] 未改动 `hooks/`、`skills.py`、非 eval 目录无关文件
- [ ] `python -m ruff check .` 通过
- [ ] 全量 pytest 不低于派活前基线

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md)
- [`harness/runner.py`](../../mini_coding_agent/harness/runner.py)
- [`tests/test_harness_fix_bug_e2e.py`](../../tests/test_harness_fix_bug_e2e.py)
