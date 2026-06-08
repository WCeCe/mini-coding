# 波次 D 实施路线图

> 返回索引：[`README.md`](./README.md) · struct 总纲：[`struct/eval-architecture-plan.md`](../struct/eval-architecture-plan.md)

本文是波次 D 的**派活与验收**文档。每项含：目标、改码范围、Done checklist、依赖、估时。

---

## 1. 优先级总览

```
P0-a  报告 pipeline_ok / failure_type / observability     [小]
P0-b  architecture schema + test_eval_contract.py         [中]
        ↓
P1-a  tests/diagnostic/test_slots_locate.py               [中]
P1-b  B1–B5 架构 bench 入库                               [中]  （可与 P1-a 并行）
        ↓
P2-a  QA_LOG + test_discovered_bugs.py                    [持续]
P2-b  Locate snippet 门槛（可选 fail）                    [中]
```

**严格顺序建议**：P0-a → P0-b → (P1-a ∥ P1-b) → P2-a 持续 → P2-b

---

## 2. P0-a：Live 报告增强

### 2.1 目标

L4 报告能回答「该改哪个节点」——读 session、输出 `failure_type`、分拆 `pipeline_ok` / `outcome_ok`。

### 2.2 改码范围

| 文件 | 改动 |
|------|------|
| `eval/run_eval.py` | `TaskResult` 新字段；`infer_failure_type()`；`run_single_task` 读 session；报告聚合 |
| `tests/test_eval_runner.py` | mock session / stderr 覆盖 taxonomy |

**不改**：harness 节点业务逻辑、tasks.json（P0-b 再改）

### 2.3 实现清单

- [x] `TaskResult` 增加 `pipeline_ok`, `outcome_ok`, `failure_type`, `observability`
- [x] `task_result_to_dict()` / JSON·Markdown 报告含新字段
- [x] `infer_failure_type(session, stderr, grading_err, task, ...)` — 顺序见 [`04-failure-taxonomy.md`](./04-failure-taxonomy.md)
- [x] `run_single_task`：`handle_ask` 后组装 `observability`
- [x] `compute_passed(..., strict_pipeline=)` 
- [x] CLI `--strict-pipeline`
- [x] Markdown 尾部 `failure_type` 聚合表 + 「建议优先改动」
- [x] JSON `summary.failure_types`
- [x] `tests/test_eval_runner.py` ≥5 个 taxonomy 用例
- [x] [`eval/README.md`](../../eval/README.md) §读报告 更新

### 2.4 规格文档

[`09-l4-live-probe-spec.md`](./09-l4-live-probe-spec.md)

### 2.5 依赖

无（可与 P0-b 并行，但 `pipeline_ok` 完整计算依赖 P0-b 的 `assert_pipeline_contract`）

### 2.6 估时

小（≈0.5–1 天）

### 2.7 验收

```bash
python -m pytest tests/test_eval_runner.py -q
# 手动：python eval/run_eval.py --task nameerror_calc --report json
# 确认 JSON 含 observability / failure_type
```

---

## 3. P0-b：architecture 契约 + L2 测试

### 3.1 目标

`tasks.json` 与 FakeModel 契约测统一；至少 3 条任务 `pipeline_ok` + `outcome_ok` 双绿。

### 3.2 改码范围

| 文件 | 改动 |
|------|------|
| `eval/task_schema.py` | **新建**：validate_task, assert_pipeline_contract, helpers |
| `eval/tasks.json` | 3 条补 `architecture` + `fake_script` |
| `tests/test_eval_contract.py` | **新建**：parametrized |
| `mini_coding_agent/.../executor.py` 或 runner | 可选：暴露 node_outputs 供 locate 断言 |

### 3.3 实现清单

- [x] `eval/task_schema.py`（或 `run_eval.py` 内 submodule）
- [x] `validate_task()` 校验 schema
- [x] `assert_pipeline_contract()` — 见 [`07-l2-contract-spec.md`](./07-l2-contract-spec.md)
- [x] `diff_changed_files`, `_count_generate_attempts` helpers
- [x] `tasks.json`：`nameerror_calc`, `off_by_one_sum`, `import_chain_rate` 补全
- [x] `FakeModelClient` 支持 `fake_script` 队列（若尚未支持）
- [x] `tests/test_eval_contract.py` parametrized 全绿
- [x] CI：`pytest tests/test_eval_contract.py` 纳入默认 pytest

### 3.4 规格文档

[`03-task-schema.md`](./03-task-schema.md) · [`07-l2-contract-spec.md`](./07-l2-contract-spec.md)

### 3.5 依赖

P0-a 可并行；locate snippet 断言可选依赖 executor 小改

### 3.6 估时

中（≈1–2 天）

### 3.7 验收

```bash
python -m pytest tests/test_eval_contract.py -v
# 3/3 passed
```

---

## 4. P1-a：L1 slots/locate 诊断

### 4.1 目标

量化门槛 D1≥90%、D2≥85%、D3=100%（有 hint 时）。

### 4.2 改码范围

| 文件 | 改动 |
|------|------|
| `tests/diagnostic/__init__.py` | 新建 |
| `tests/diagnostic/test_slots_locate.py` | SL/L 系列 parametrized |
| 可选：`tests/diagnostic/test_gate_parse.py` 等 | 见 [`06-l1-diagnostic-spec.md`](./06-l1-diagnostic-spec.md)

### 4.3 实现清单

- [x] `tests/diagnostic/` 目录
- [x] ≥20 slots 样本（SL-01–SL-24 子集）
- [x] locate 样本 L-01–L-07
- [x] session 级准确率汇总或 document 门槛
- [x] 与 `test_harness_locate_snippets.py` 不重复（diagnostic=量化，harness=行为）

### 4.4 规格文档

[`06-l1-diagnostic-spec.md`](./06-l1-diagnostic-spec.md)

### 4.5 依赖

无

### 4.6 估时

中（≈1–2 天）

---

## 5. P1-b：B1–B5 架构 bench

### 5.1 目标

5 条 dimension 任务入库，L2 契约全绿。

### 5.2 改码范围

| 文件 | 改动 |
|------|------|
| `eval/tasks.json` | +4 新任务；`import_chain_rate` 升格 B5 |
| `tests/test_eval_contract.py` | 自动覆盖新 fake_script 任务 |

### 5.3 实现清单

- [x] B1 `bench_retry_off_by_one`
- [x] B2 `bench_decoy_calc_backup`
- [x] B3 `bench_gate_explain_boundary`
- [x] B4 `bench_no_rig_search`
- [x] B5 `import_chain_rate` + dimension + architecture
- [x] 每条 fake_script patch old_text 与 setup 一致
- [x] B4 测试 setup 无 index.db
- [x] 5/5 contract pass

### 5.4 规格文档

[`08-l3-arch-bench-spec.md`](./08-l3-arch-bench-spec.md)

### 5.5 依赖

P0-b

### 5.6 估时

中（≈1–2 天）

---

## 6. P2-a：踩坑固化

### 6.1 目标

历史 + 新 bug 有 regression class；QA_LOG 持续更新。

### 6.2 改码范围

| 文件 | 改动 |
|------|------|
| `docs/eval/QA_LOG.md` | 持续追加（已初始化轮次 0） |
| `tests/regression/test_discovered_bugs.py` | **新建**，≥3 class |

### 6.3 实现清单

- [x] `tests/regression/` 目录
- [x] 轮次 0 至少 3 条转 TestBug_* class（verify 假阳、protocol、patch match）
- [x] 流程文档化：live 新失败 → QA_LOG → regression

### 6.4 规格文档

[`QA_LOG.md`](./QA_LOG.md)

### 6.5 依赖

P0-b（L2 可复现）

### 6.6 估时

持续

---

## 7. P2-b：Locate snippet 门槛

### 7.1 目标

契约任务在无有效 snippet 时 locate **fail**，而非拖到 generate。

### 7.2 改码范围

| 文件 | 改动 |
|------|------|
| `mini_coding_agent/modes/graph/nodes/locate.py` | 可选 fail 逻辑 |
| `tests/test_harness_locate_snippets.py` | 更新 |
| `tests/test_eval_contract.py` | B4 断言 |

### 7.3 实现清单

- [x] `architecture.locate.min_snippets_with_source_lines` 驱动 fail
- [x] **默认**仅对含 architecture.locate 的任务启用
- [x] B4 / no_rig 契约测更新
- [x] [`phase5-graph.md`](../struct/phase5-graph.md) §7 与实现一致

### 7.4 依赖

P1-a、P1-b

### 7.5 估时

中（≈1 天）

---

## 8. 波次 D 结项 Done Definition

- [x] P0-a：报告字段 + infer_failure_type + 测试
- [x] P0-b：≥3 任务 architecture + fake_script + contract 全绿
- [x] P1-a：diagnostic D1–D3 门槛达标
- [x] P1-b：B1–B5 入库且 contract 全绿
- [x] P2-a：QA_LOG + ≥3 regression class
- [x] P2-b：Locate 门槛（至少契约任务）
- [x] [`05-pipeline-checklist.md`](./05-pipeline-checklist.md) 无未 defer 的 📋 项
- [x] `eval/README.md` + struct 状态更新为结项
- [x] 全量 pytest + ruff 不低于派活前基线
- [x] 无新增 pip 依赖
- [ ] Live 基线表更新（15 条可选）

---

## 9. 文件清单（规划态）

```
eval/
├── run_eval.py              # P0-a 扩展
├── task_schema.py           # P0-b 新建
├── tasks.json               # P0-b/P1-b 扩展
└── README.md                # 更新

tests/
├── diagnostic/              # P1-a
│   └── test_slots_locate.py
├── test_eval_contract.py    # P0-b
├── test_eval_runner.py      # P0-a 扩展
└── regression/              # P2-a
    └── test_discovered_bugs.py

docs/eval/                   # 本文档体系 ✅
└── ...

mini_coding_agent/modes/graph/nodes/locate.py  # P2-b 可选
```

---

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| fake_script patch old_text 与 setup 不一致 | 入库前单跑 contract；CI 绿 |
| P0-a 与 P0-b pipeline_ok 循环依赖 | P0-a 先实现 observability；pipeline_ok 待 P0-b 接上 |
| locate 门槛破坏现有 E2E | 仅 architecture 任务启用 |
| live 全挂 | 文档诚实；看 failure_type 改架构 |
| executor 暴露 node_outputs 改码面 | 可先 B 方案 stderr 推断，后补 A |

---

## 11. 下一步行动（建议）

1. **立即可做**：P0-a `infer_failure_type` + observability（不改 tasks.json）
2. **接着**：P0-b 三条契约任务 + `test_eval_contract.py`
3. **然后**：P1-a ∥ P1-b 并行
4. **持续**：每轮 live 更新 QA_LOG

---

*10-implementation-roadmap.md · 波次 D · 2026-06-05*
