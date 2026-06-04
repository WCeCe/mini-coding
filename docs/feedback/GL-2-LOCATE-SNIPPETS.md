# GL-2-LOCATE-SNIPPETS — 子 Agent 回报

---

## 元信息

- **TASK_ID**: GL-2-LOCATE-SNIPPETS
- **状态**: 完成

---

## 方案摘要（IMPLEMENT 必填）

1. **新增 `harness/snippet.py`**：统一 snippet 格式（`# file: path L10-L30` + read_file 行号正文）；`read_snippet` / `read_snippet_for_hit`（RIG `lineno`/`end_lineno` ±10，单段 ≤120 行）；`parse_search_hits` + `snippets_from_search`（rg `path:line:content` → 合并区间后 read_file）；`has_source_lines`（`re.MULTILINE` 匹配 `   N:` 行）。

2. **重写 `harness/nodes/locate.py`**：
   - RIG symbol/file 命中：`read_snippet_for_hit`，前缀 `# rig: …` + 源码（非仅 metadata）。
   - 无 rig.db：search 命中后按行 ±10 读源码。
   - `files_hint` / neighbor：经 `read_snippet`；`_ensure_source_snippet` 在无源码片段时对首个 `.py` 读 1–120 行。
   - `seen_ranges` 去重同一文件区间；Locate **无 LLM**。

3. **测试**：`tests/test_harness_locate_snippets.py`（3 条）；`test_rig.py::test_locate_uses_rig_when_db_exists` 增加 `has_source_lines` 断言。

未改动 Hook、Skill、非 fix_bug 模板、Generate/Gate/Verify。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| 无 rig.db + symbols_hint → 含源码行 | ✅ | `test_locate_without_rig_symbol_hint_has_source_snippets` |
| 有 rig.db + symbol 命中 → 含代码正文 | ✅ | `test_locate_with_rig_symbol_hit_has_code_not_only_metadata` |
| traceback files_hint 不退化 | ✅ | `test_locate_files_hint_traceback_still_reads_source` |
| `test_harness_fix_bug_e2e` 仍绿 | ✅ | 7 passed |
| `test_rig.py` 仍绿 | ✅ | 含更新后的 rig locate 测 |
| GL-1 eval FakeModel pass | ✅ | `run_eval.py --fake` 1/1 |
| ruff + 全量 pytest | ✅ | 见验证结果 |
| Locate 无 LLM | ✅ | 仅 `run_tool(search/read_file)` |

---

## 交付物

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/harness/snippet.py` | 片段读取与 search 解析 |
| `mini_coding_agent/harness/nodes/locate.py` | RIG/search/files_hint 加固 |
| `tests/test_harness_locate_snippets.py` | GL-2 验收单测 |
| `tests/test_rig.py` | locate rig 断言补充 |
| `docs/feedback/GL-2-LOCATE-SNIPPETS.md` | 本回报 |

---

## 验证结果

```
$ python -m pytest tests/test_harness_locate_snippets.py tests/test_rig.py tests/test_harness_fix_bug_e2e.py tests/test_eval_runner.py -q
........................                                                 [100%]
24 passed in 21.50s
```

```
$ python -m pytest -q
........................................................................ [ 44%]
............s........................................................... [ 88%]
...................                                                      [100%]
162 passed, 1 skipped in 111.42s (0:01:51)
```

```
$ python -m ruff check .
All checks passed!
```

```
$ python eval/run_eval.py --fake
# Eval 报告
| nameerror_calc | pass | — | — | 1059 |
**合计**：1/1 通过
```

---

## 风险与未解决问题

- traceback 中 `in (\w+)$` 会提取函数名（如 `add`）为 `symbols_hint`，可能多一次 search；不影响正确性，仅多 snippet。
- Windows 无 `rg` 时走 Python 逐文件搜索，大仓库可能较慢（与 Phase 5 行为一致）。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-04 主 Agent 复验：locate 3 测 + rig/e2e/eval 24 测绿；`--fake` 1/1；snippet.py 统一 `# file: … Lx-Ly` + 源码正文，RIG/search/files_hint 三路径均满足 §7.2 GL-2。Wave 2 仍待 GL-3、GL-4 feedback。
