# GL-3-VERIFY-ERROR-FORMAT — 子 Agent 回报

---

## 元信息

- **TASK_ID**: GL-3-VERIFY-ERROR-FORMAT
- **状态**: 完成

---

## 方案摘要（IMPLEMENT 必填）

1. **新增 `harness/error_format.py`**：`format_error_for_model(raw)` 将 verify 长输出压缩为 ≤8 行、≤800 字符摘要。
   - **py_compile**：解析 `py_compile 失败：` 前缀，保留 `path:lineno` + `SyntaxError` 行及 `^` 上下文。
   - **pytest/shell**：优先读 `stderr:`/`stdout:` 段，自 traceback 末尾向上提取 `File "…", line N` 与最终 `*Error` 行。
   - **兜底**：取末 8 行；仍无法解析则 `clip(raw, 800)`。

2. **`harness/executor.py`**：verify 失败分支仅改一行——`ctx.last_verify_error = format_error_for_model(result.message)`。未动 `_resolve_final`（留给 GL-4）。

3. **Generate**：已读 `ctx.last_verify_error`，无需改动。

4. **测试** `tests/test_harness_error_format.py`：4 条单测覆盖 pytest 长 log、py_compile、fallback clip、retry prompt 不含巨型 log。

未改动 Hook、Skill、Generate/Verify 节点逻辑。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据（测试名 / 行为说明） |
|------|----------|---------------------------|
| 长 pytest → 含错误类型 + 文件 + 行号 | ✅ | `test_format_long_pytest_traceback_has_type_file_line` |
| py_compile → 可读摘要 | ✅ | `test_format_py_compile_error_is_readable` |
| verify 失败写入格式化摘要 | ✅ | `executor.py` L45；`test_verify_retry_prompt_uses_summary_not_full_log` |
| retry prompt 不含未截断巨型 log | ✅ | 同上；`frame_199` 不在第二次 prompt |
| `test_verify_retry_runs_generate_twice` 仍绿 | ✅ | 见验证结果 |
| 不改 Hook/Skill | ✅ | 仅 harness 包 2 文件 + 新测 |
| ruff 通过 | ✅ | 见验证结果 |

---

## 交付物

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/harness/error_format.py` | `format_error_for_model()` |
| `mini_coding_agent/harness/executor.py` | verify 失败处接入格式化（仅 1 行 + import） |
| `tests/test_harness_error_format.py` | GL-3 验收单测 |
| `docs/feedback/GL-3-VERIFY-ERROR-FORMAT.md` | 本回报 |

---

## 验证结果

```
$ python -m pytest tests/test_harness_error_format.py tests/test_harness_fix_bug_e2e.py::test_verify_retry_runs_generate_twice -q
.....                                                                    [100%]
5 passed in 3.89s
```

```
$ python -m pytest -q
.............................................................F........F. [ 43%]
...F............s....................................................... [ 86%]
.......................                                                  [100%]
================================== FAILURES ===================================
_____________________ test_plan_for_each_intent[fix_bug] ______________________
... fix_bug 节点列表期望含 review，与 GL-4 已去掉 review 的 fix_bug.json 不一致
______________ test_consecutive_asks_read_last_gate_from_session ______________
... 仍 mock review final，与无 review 黄金路径不一致（GL-4 范围）
______________ test_observe_post_node_records_harness_last_node _______________
... 期望 harness_last_node.type == review，GL-4 后末节点为 verify
=========================== short test summary info ===========================
FAILED tests/test_harness_planner.py::test_plan_for_each_intent[fix_bug]
FAILED tests/test_harness_session.py::test_consecutive_asks_read_last_gate_from_session
FAILED tests/test_harness_session.py::test_observe_post_node_records_harness_last_node
3 failed, 163 passed, 1 skipped in 150.48s (0:02:30)
```

```
$ python -m ruff check .
All checks passed!
```

**说明**：3 个失败为 **GL-4 并行** 改 `fix_bug.json` 去掉 review 后，planner/session 单测尚未同步；与 GL-3 改动无关。GL-3 相关 5 项测试全绿。

---

## 风险与未解决问题

- **并行冲突**：工作区已含 GL-4 的 `fix_bug.json`（无 review）及 `_resolve_final` verify 分支；本任务仅 touch `last_verify_error` 行，无 merge 冲突。
- **摘要启发式**：极端非标准 shell 输出可能仅落至 generic 末 8 行；契约允许 clip 兜底。
- **全绿 pytest**：需 GL-4 同步 `test_harness_planner.py` / `test_harness_session.py` 后恢复。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-04 主 Agent 复验：GL-3 专项 5/5 绿；`executor.py` 仅改 `format_error_for_model` 一行，未越界 `_resolve_final`。子 Agent 提交时 3 fail 为 GL-4 并行所致；GL-4 测试同步后全量 **166 passed**。GL-3 结项。
