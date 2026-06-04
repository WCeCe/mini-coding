# GL-1-EVAL-INFRA — 子 Agent 回报

---

## 元信息

- **TASK_ID**: GL-1-EVAL-INFRA
- **状态**: 完成

---

## 方案摘要（IMPLEMENT 必填）

建立 `eval/` 目录，实现可重复的 fix_bug 度量框架：

1. **`eval/tasks.json`**：按 `phase5-graph.md` §6 定义 `nameerror_calc`（NameError + calc.py setup/expect + `py_compile`）。
2. **`eval/run_eval.py`**：
   - 每任务 `tempfile.TemporaryDirectory` 隔离；写入 `setup_files` + `README.md`。
   - 构建 `MiniAgent`（`approval_policy=auto`、`enable_trace_hook=False`）。
   - `--fake`：由 `setup_files`/`expect_files` 推导 FakeModel 队列（Gate JSON → `patch_file` 最小 diff → review `<final>`）。
   - 调用 `handle_ask(..., harness_enabled=True)`；捕获 stderr 推断失败环节。
   - 事后断言 `expect_files` 精确匹配 + 任务级 `verify`（`py_compile`/`pytest`/`none`）。
   - `--live` 预留 `OllamaModelClient`（GL-5 使用）；`--task`/`--report markdown|csv`。
3. **`tests/test_eval_runner.py`**：加载任务、Fake 输出顺序、单任务/全量 pass、报告字段、CLI 子进程 `--fake`。
4. **未改动** Hook、Skill、Gate/Locate/Generate/Verify 业务逻辑；无新 pip 依赖。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据（测试名 / 行为说明） |
|------|----------|---------------------------|
| `tasks.json` ≥1 个 nameerror_calc | ✅ | `test_load_tasks_has_nameerror_calc` |
| `handle_ask(..., harness_enabled=True)` + `approval_policy=auto` | ✅ | `build_eval_agent` + `run_single_task` |
| 每任务独立 temp 目录 | ✅ | `run_single_task` 使用 `TemporaryDirectory` |
| 报告含 task_id、pass/fail、失败步、耗时 | ✅ | `format_report_markdown` / `test_report_contains_task_id_and_status` |
| `python eval/run_eval.py --fake` 1/1 pass | ✅ | `test_run_eval_cli_fake_subprocess`；CLI exit 0 |
| `test_eval_runner.py` 全绿 | ✅ | 8 passed |
| 未改 hooks/skills/harness 节点业务 | ✅ | 仅新增 `eval/`、`tests/test_eval_runner.py`、本 feedback |
| 无新 pip 依赖 | ✅ | 标准库 + 现有包 |
| 全量 pytest 不低于基线 | ✅ | 159 passed, 1 skipped（+8 eval 测） |
| ruff 通过 | ✅ | 见验证结果 |

---

## 交付物

| 路径 | 说明 |
|------|------|
| `eval/tasks.json` | `nameerror_calc` 任务定义 |
| `eval/run_eval.py` | CLI：`--fake`、`--live`、`--task`、`--report` |
| `eval/README.md` | 用法、字段、Fake 队列说明 |
| `tests/test_eval_runner.py` | FakeModel 框架单测（8 条） |
| `docs/feedback/GL-1-EVAL-INFRA.md` | 本回报 |

---

## 验证结果

```
$ python -m pytest tests/test_eval_runner.py -q
........                                                                 [100%]
8 passed in 7.97s
```

```
$ python eval/run_eval.py --fake
# Eval 报告

| 任务 | 结果 | 失败环节 | 原因 | 耗时(ms) |
|------|------|----------|------|----------|
| nameerror_calc | pass | — | — | 1307 |

**合计**：1/1 通过
```

```
$ python -m pytest -q
........................................................................ [ 45%]
.........s.............................................................. [ 90%]
................                                                         [100%]
159 passed, 1 skipped in 102.96s (0:01:42)
```

```
$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- **Windows 控制台编码**：子进程捕获 stdout 时中文表头可能乱码，但 exit code、`nameerror_calc`、`| pass |`、`1/1` 可判定；UTF-8 终端下 Markdown 正常。
- **review 节点仍消耗 1× Fake 输出**：当前 `fix_bug.json` 含 review；GL-4 瘦身后可缩短 Fake 队列。
- **`--live`**：已实现参数与 `OllamaModelClient` 接线，真实基线留 GL-5。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-04 主 Agent 独立复验：`test_eval_runner.py` 8/8、`run_eval.py --fake` exit 0（1/1 pass）、ruff 通过。交付物齐全，未越界改动 Hook/Skill/Harness 节点。Wave 2（GL-2/GL-3/GL-4）已授权派发。
