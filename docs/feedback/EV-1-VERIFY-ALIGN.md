# EV-1-VERIFY-ALIGN — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-1-VERIFY-ALIGN
- **状态**: 完成

---

## 方案摘要

### 问题

GL-5 `off_by_one_sum` 暴露 harness/eval **双标准**：harness `verify` 仅对改动文件做 `py_compile`，错误修复（`range(1, n+2)`）仍报 ok；eval 终判在 `expect_files` 阶段才 fail。4/5 条 easy 任务 harness 不验语义。

### 设计决策

1. **抽取共用模块 `verify_rules.py`**（graph 包内，无新 pip 依赖）
   - `resolve_test_command`：优先 `dag.slots.test_command`（`fill_slots` → `detect_test_command`），否则按工作区 `tests/` / `pytest.ini` 探测。
   - `run_task_verify` / `run_pytest` / `run_py_compile_all`：供 eval 终判直接调用。
   - `collect_tests_snapshot` + `check_tests_snapshot_unchanged` + `check_generate_did_not_touch_tests`：实现 `lock_tests` 基础行为。

2. **harness `verify.py` 决策顺序**
   1. `lock_tests`：generate 路径在 `tests/` 下 → fail
   2. `lock_tests`：tests/ 快照与 DAG 启动基线不一致 → fail
   3. 有测试命令（slots 或探测）→ **shell 执行 pytest**（`method: shell`），不以 py_compile 提前成功
   4. 无测试套件 → 对改动 `.py` 做 `py_compile`（原行为保留）

3. **executor 启动时采集 `test_baseline`**
   - `HarnessContext.test_baseline = collect_tests_snapshot(root)`，供 verify 对比。

4. **eval `run_eval.py` 终判对齐**
   - `check_task_verify` → `run_task_verify`（与 harness 语义一致）
   - `check_lock_tests` → `check_lock_tests_from_setup`（含 tests/ 的任务默认锁定测试文件）
   - 判定顺序：lock_tests → expect_files → task verify

### 改动文件

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/modes/graph/verify_rules.py` | **新增** 共用 verify / lock_tests 规则 |
| `mini_coding_agent/modes/graph/nodes/verify.py` | pytest 优先、lock_tests 前置 |
| `mini_coding_agent/modes/graph/executor.py` | 启动时采集 `test_baseline` |
| `eval/run_eval.py` | 终判调用共用规则；`infer_failure_step` 识别 lock_tests |
| `tests/test_harness_verify_align.py` | **新增** 10 条 EV-1 回归测 |

未改 Gate / Locate / Generate 业务逻辑（verify 调用链与 executor 基线采集除外）。

---

## 验收自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| 有 `tests/` 时 harness 执行 pytest | ✅ | `test_wrong_fix_py_compile_ok_but_pytest_fails`、`test_correct_fix_with_tests_passes_verify` |
| `off_by_one_sum` 错误修复 harness verify fail | ✅ | `test_harness_e2e_wrong_fix_verify_fails`（`last_verify.ok is False`） |
| 测试文件被 patch / 篡改 → fail | ✅ | `test_lock_tests_rejects_*`、`test_run_eval_lock_tests_detects_tampered_test` |
| `--fake` 全绿 | ✅ | 5/5 通过 |
| pytest + ruff | ✅ | 见下方完整输出 |
| 全量 pytest ≥ 派活前基线（167） | ✅ | **177 passed**, 1 skipped（+10 EV-1 测） |

### 关键回归场景（`off_by_one_sum` 类）

- **错误修复** `range(1, n+2)`：py_compile 过，pytest 失败 → harness verify **fail**（`method: shell`），不再假阳性 ok。
- **正确修复** `range(1, n+1)`：pytest 通过 → harness verify ok。
- **无 tests/** 任务（如 `nameerror_calc`）：仍走 py_compile，行为不变。

---

## 验证结果

### `python eval/run_eval.py --fake`

```
| nameerror_calc | pass | — | — | … |
| syntaxerror_paren | pass | — | — | … |
| nameerror_greet | pass | — | — | … |
| off_by_one_sum | pass | — | — | … |
| wrong_operator_calc | pass | — | — | … |

**合计**：5/5 通过
```

### `python -m pytest tests/test_harness_verify_align.py -q`

```
..........                                                               [100%]
10 passed in 21.13s
```

### `python -m pytest -q`（全量）

```
........................................................................ [ 40%]
...........................s............................................ [ 80%]
..................................                                       [100%]
177 passed, 1 skipped in 169.06s (0:02:49)
```

### `python -m ruff check .`

```
All checks passed!
```

---

## 风险与后续

- harness verify 经 `run_shell` 跑 pytest，eval 终判经 `subprocess`；语义一致，输出格式略有差异（不影响 pass/fail）。
- `lock_tests` 字段正式写入 `tasks.json` 留待 **EV-2**；当前对含 `tests/` 的 setup 默认启用。
- `grading: tests_only` 与 FakeModel 队列调整留待 **EV-2**。

---

*EV-1-VERIFY-ALIGN · 子 Agent · 2026-06-05*
