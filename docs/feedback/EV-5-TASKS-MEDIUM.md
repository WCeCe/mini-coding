# EV-5-TASKS-MEDIUM — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-5-TASKS-MEDIUM
- **状态**: 完成
- **依赖**: EV-2-GRADING-SCHEMA ✅、EV-4-TASKS-EASY ✅

---

## 方案摘要

### 目标

新增 **≥3 条** `tier: medium` 的 `fix_bug` 任务，覆盖 Locate / 推理（非仅 Generate）；三类场景各 ≥1；默认 `grading: tests_only`；`--fake` 全绿。

### 设计决策

1. **沿用 `eval/tasks.json` 单文件** — medium 3 条追加在 easy 12 条之后，不拆目录。
2. **全部 `tests_only` + `lock_tests: true` + `verify: pytest`** — 符合 eval-repair-plan §3 medium 默认评分；含 `tests/` 防 agent 改测。
3. **Fake 队列** — 三条均有 `expect_files`（含单文件或多文件 patch 参考），`build_fake_outputs` 反推 patch；`import_chain_rate` 仅 patch `rates.py`（bug 在 A，表现于 B）。
4. **live 预期** — medium 需 Locate / 多文件推理；`--live` 下 0/N 可接受，文档已标明「medium live 预期低于 easy」。

### 新增 3 条 medium 任务

| id | 场景 | grading | verify | 要点 |
|----|------|---------|--------|------|
| `no_file_hint_add` | 消息不点名文件 | tests_only | pytest | 无 `File "…"` / 无 `.py` 路径；须从 `add(2,3)` 推断 `calc.py` |
| `import_chain_rate` | 两文件 import 链 | tests_only | pytest | bug 在 `rates.py`（缺 `/100`），pytest 失败于 `app.compute` |
| `logic_median_even` | 逻辑错、语法对 | tests_only | pytest | `py_compile` 可通过；偶数长度 median 取错中位 |

全任务集 **15 条**（easy 12 + medium 3）。

### 改动文件

| 路径 | 说明 |
|------|------|
| `eval/tasks.json` | +3 medium 任务 |
| `eval/README.md` | medium 表 3 条、live 预期说明、合计 15 条 |
| `tests/test_eval_runner.py` | medium tier/grading 断言、三类场景测、fake pass 参数化 |
| `docs/feedback/EV-5-TASKS-MEDIUM.md` | 本回报 |

未改 `run_eval.py` / harness 业务逻辑（复用 EV-2 grading schema）。

---

## 验收自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| medium ≥3 条 | ✅ | 3 条，`tier: medium` |
| 消息不点名文件 ≥1 | ✅ | `no_file_hint_add`，`test_medium_no_file_hint_message_has_no_traceback_path` |
| import 链 ≥1 | ✅ | `import_chain_rate`，`test_medium_import_chain_has_two_source_files` |
| 逻辑错语法对 + pytest ≥1 | ✅ | `logic_median_even`，`grading: tests_only` + `verify: pytest` |
| medium 默认 tests_only | ✅ | `test_medium_tasks_tier_and_grading` |
| `--fake` 全绿 | ✅ | 见下方 15/15 |
| README 标明 medium live 低于 easy | ✅ | `eval/README.md` medium 节 |
| pytest + ruff | ✅ | 见下方 |
| 无新增 pip 依赖 | ✅ | 仅 tasks.json + 测 + 文档 |

---

## 验证结果

### `python eval/run_eval.py --fake`

```
**合计**：15/15 通过
```

（12 easy + 3 medium 全绿；medium 单条耗时略高：`import_chain_rate` ~27s）

### `python -m pytest tests/test_eval_runner.py -q`

```
30 passed in 194.39s
```

含：`test_medium_tasks_tier_and_grading`、`test_medium_no_file_hint_message_has_no_traceback_path`、`test_medium_import_chain_has_two_source_files`、`test_medium_tasks_fake_pass`（×3）。

### `python -m ruff check .`

```
All checks passed!
```

---

## Live（可选，未阻塞验收）

本机未在本轮跑 `--live`。按契约与 EV-4 基线（easy live **2/5**），**medium 0/3 为可接受预期**；后续 EV-6 基线对比时再归档分步报告。

---

## 主 Agent 复审

- **结论**: **通过**
- **备注**: 2026-06-05 medium 3 条；三类场景齐全；live 未跑为可接受预期。
