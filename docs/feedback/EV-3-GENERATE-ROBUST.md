# EV-3-GENERATE-ROBUST — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-3-GENERATE-ROBUST
- **状态**: 完成

---

## 方案摘要

针对 GL-5 live **2/5** 中两类 Generate 主失败，小步增强协议解析与 fix_bug patch 对齐：

### 1. `protocol.py` — tool JSON 容错

| 失败模式 | 改动 |
|----------|------|
| `nameerror_greet`：合法-looking `<tool>{...}</tool>` 因 f-string / 尾 `}` 导致 `json.loads` 失败 | `_parse_tool_json_relaxed`：先剥多余 `}` 再 `json.loads`；失败时用正则抽取 `patch_file`/`write_file` 字段 |
| JSON 与 XML 双路径 | `<tool>` JSON 解析失败时 **fall-through** 到 `parse_xml_tool`，不再立即 retry |

### 2. `generate.py` — fix_bug old_text 对齐

| 失败模式 | 改动 |
|----------|------|
| `syntaxerror_paren`：old_text 0 次匹配（缺缩进 / 尾随空白 / 字面 `\n`） | `_normalize_patch_args_for_fix_bug`：在 `run_tool` 前尝试有限候选（rstrip、strip、唯一行匹配、唯一子串行、locate snippet 行）；**仅** `fix_bug` + `patch_file` |
| 提示 | fix_bug prompt 补充「old_text 须与定位上下文逐字一致（含缩进）」 |

**未改**：`validators.py` governance（仍要求 old_text 恰好 1 次）；不引入「任意文本可匹配」。

---

## 改动文件

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/platform/protocol.py` | JSON tool 宽松解析 + fall-through |
| `mini_coding_agent/modes/graph/nodes/generate.py` | fix_bug patch old_text 对齐 + prompt |
| `tests/test_generate_robust.py` | **新增** 4 条 GL-5 类回归 |
| `docs/feedback/EV-3-GENERATE-ROBUST.md` | 本回报 |

---

## 验收自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| pytest ≥2 条对应 syntaxerror_paren / nameerror_greet 类 | ✅ | `test_protocol_parse_patch_file_*` ×2 + `test_generate_fix_bug_aligns_*` |
| harness E2E + eval fake 全绿 | ✅ | 见下方 |
| live 复跑记录 | ✅ | 见「Live 复跑」 |
| pytest + ruff | ✅ | 见下方 |

---

## 验证结果

### `python -m pytest tests/test_generate_robust.py -q`

```
4 passed
```

### `python -m pytest -q`（全量）

```
186 passed, 1 skipped
```

### `python -m ruff check .`

```
All checks passed!
```

### `python eval/run_eval.py --fake`

```
**合计**：5/5 通过
```

---

## Live 复跑（`qwen2.5-coder:7b`，逐 task）

**环境**：Windows，Ollama `http://127.0.0.1:11434`，`--ollama-timeout 180`。

| task_id | GL-5 基线 | EV-3 后 | 失败环节 | 备注 |
|---------|-----------|---------|----------|------|
| syntaxerror_paren | fail | **fail** | generate → expect_files | old_text 仍 0 匹配（~338s）；小模型片段与文件无唯一对齐关系 |
| nameerror_greet | fail | **fail** | generate | stderr 片段含 f-string JSON；**同片段 pytest 已可 parse 为 tool**（~155s），live 或仍有模型输出微差 / 方差 |

**对比 GL-5 表**：基线 **2/5**；EV-3 复跑 **0/2**（仅测原 fail 两条）。不保证刷分。单元测试已钉住「尾 `}` / f-string 解析」与「缺缩进 old_text 对齐」。

### 典型命令

```bash
python eval/run_eval.py --live --model qwen2.5-coder:7b --ollama-timeout 180 --task syntaxerror_paren
python eval/run_eval.py --live --model qwen2.5-coder:7b --ollama-timeout 180 --task nameerror_greet
```

---

## 风险与未解决问题

- **syntaxerror_paren live**：模型 old_text 若与文件无唯一子串关系，对齐逻辑 intentionally 不强行 patch（避免 governance 误改）。
- **off_by_one_sum**：属改码内容偏题，非本任务范围（EV-1 已对齐 verify）。
- 后续可考虑：Generate prompt 附「从 snippet 复制一行作为 old_text」示例（需主 Agent 批准扩 prompt）。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-05 复验：pytest 186 passed；protocol/generate 回归测 4 条；live 两条原 fail 仍 fail（符合「不刷分」预期），单元测试已钉住解析/对齐路径。
