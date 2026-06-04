# GL-4-FIX-BUG-SLIM — 子 Agent 回报

---

## 元信息

- **TASK_ID**: GL-4-FIX-BUG-SLIM
- **状态**: 完成

---

## 方案摘要（IMPLEMENT 必填）

采用 **方案 A**（struct §7.2 GL-4 推荐）：直接修改 `fix_bug.json`，不新增 `fix_bug_golden.json`。

1. **`fix_bug.json`**：DAG 为 `locate → generate → verify`，删除 `review` 节点；保留 `verify→generate` retry（max 2）。
2. **`executor._resolve_final`**：仍优先 `review` / `explain`（供 generate_code、refactor、project_ops 等模板）；无 review 且 `verify` 成功时，从 `verify.data["paths"]` 或 `_modified_python_paths` 拼中文终态：`已修复并通过验证：{paths}`。
3. **FakeModel 队列**：Gate + Generate（+ 可选 retry Generate），不再追加 review `<final>`。
4. **`review.py` 未删**；其他意图模板未改。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据（测试名 / 行为说明） |
|------|----------|---------------------------|
| fix_bug FakeModel 无需 review mock | ✅ | `test_fix_bug_e2e_harness_pipeline`；`test_verify_retry_runs_generate_twice`（2 次 prompt） |
| verify 通过后非空中文 `final_text` | ✅ | 含「已修复并通过验证」与 `calc.py` |
| 其他意图 review 不受影响 | ✅ | `EXPECTED_NODE_TYPES` 中 generate_code/refactor/project_ops 仍含 review；`test_harness_five_intents` 全绿 |
| `review.py` 保留 | ✅ | 未改 `harness/nodes/review.py` |
| 非 fix_bug 模板未改 | ✅ | 仅 `fix_bug.json` |
| `eval/run_eval.py --fake` 1/1 | ✅ | CLI exit 0，`nameerror_calc` pass |
| 全量 pytest + ruff | ✅ | 166 passed, 1 skipped；ruff All checks passed |

---

## 交付物

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/harness/templates/fix_bug.json` | 去掉 review 节点 |
| `mini_coding_agent/harness/executor.py` | `_resolve_final` verify 成功分支 |
| `tests/test_harness_fix_bug_e2e.py` | Fake 队列与断言 |
| `eval/run_eval.py` | `build_fake_outputs` 少 review；降级检测改匹配新终态 |
| `tests/test_eval_runner.py` | Fake 输出长度为 2 |
| `tests/test_harness_planner.py` | fix_bug 期望拓扑 |
| `tests/test_harness_session.py` | 末节点为 verify；连续 ask 队列 |
| `tests/test_harness_five_intents.py` | fix_bug 分支去 review mock |
| `docs/feedback/GL-4-FIX-BUG-SLIM.md` | 本回报 |

---

## 验证结果

```
$ python -m pytest -q
........................................................................ [ 43%]
................s....................................................... [ 86%]
.......................                                                  [100%]
166 passed, 1 skipped in 138.16s (0:02:18)
```

```
$ python -m ruff check .
All checks passed!
```

```
$ python eval/run_eval.py --fake
# Eval 报告

| 任务 | 结果 | 失败环节 | 原因 | 耗时(ms) |
|------|------|----------|------|----------|
| nameerror_calc | pass | — | — | 1849 |

**合计**：1/1 通过
```

```
$ python -m pytest tests/test_harness_fix_bug_e2e.py tests/test_eval_runner.py -q
................                                                         [100%]
16 passed
```

---

## 风险与未解决问题

- **`eval/README.md`** 仍写「3. Review `<final>`」；GL-5 或文档扫尾时可同步（本任务交付清单未要求改 README）。
- **主 README** 中 fix_bug 拓扑描述仍含 review；struct 状态板待 GL-REVIEW 统一更新。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-04 主 Agent 复验：fix_bug.json 无 review；`_resolve_final` verify 成功返回中文终态；eval `--fake` 1/1；全量 pytest **166 passed**；五类意图中仅 fix_bug 瘦身，review.py 保留。GL-4 结项。
