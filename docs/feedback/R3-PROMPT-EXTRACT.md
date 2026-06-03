# 子 Agent 回报：R3-PROMPT-EXTRACT

## 元信息

- **TASK_ID**: R3-PROMPT-EXTRACT
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

将 Prompt 形状相关逻辑整段迁至 **`mini_coding_agent/prompt.py`**，agent 保留薄委托与对外 API（`build_prefix` / `memory_text` / `history_text` / `prompt`），供 CLI `/memory` 与测试继续调用。

**模块函数**

| 函数 | 入参 | 职责 |
|------|------|------|
| `build_prefix(tools, skill_catalog, workspace)` | tools dict、SkillCatalog、WorkspaceContext | 规则 / 工具清单 / 示例 / metadata / 仓库快照 |
| `memory_text(memory)` | session memory dict | task、files、plan、loaded_skills、notes |
| `history_text(history)` | session history list | 去重 read、截断、MAX_HISTORY |
| `build_prompt(prefix, memory, history, user_message)` | 四段输入 | 组装完整 prompt（等价原 `prompt()`） |

**agent 委托**

- `__init__` 仍 `self.prefix = self.build_prefix()`（行为不变）
- `ask()` 仍 `self.prompt(user_message)` → 内部 `build_prompt(...)`
- `tool_delegate` 仍 `self.history_text()` 委托

无循环 import：`prompt.py` 仅依赖 constants、planning、skills、util。

---

## 模块 map

| 模块 | 职责（R3 后） |
|------|----------------|
| `mini_coding_agent/prompt.py` | **新建**。prefix / memory / history / prompt 组装 |
| `mini_coding_agent/agent.py` | 编排：薄委托 prompt；ask / run_tool 未动 |
| `mini_coding_agent/protocol.py` | R1 不变 |
| `mini_coding_agent/governance.py` | R2 不变 |
| `tests/test_mini_coding_agent.py` | 无改动（经 agent 方法覆盖） |

**行数**：`agent.py` ~873 → ~741（−132）；`prompt.py` 新建 ~162 行。

---

## 注释迁移说明

| 原位置（`agent.py`） | 处置 |
|----------------------|------|
| `#构建prompt的prefix部分…` 及 `build_prefix` 内全部注释（tool_lines、examples、rules、prefix 五段结构） | **迁入** `prompt.build_prefix` |
| `#构建memory（含 Phase 3 plan…` 及 plan / loaded_skills 注释 | **迁入** `prompt.memory_text` |
| `#### 4) Context Reduction…` 段标题 + `#获取历史信息` 及 `history_text` 内去重/截断注释 | **迁入** `prompt.py`（history_text 前） |
| `#### 2) Prompt Shape… (Continued)` + `#prompt分为四个部分…` | **迁入** `prompt.py`（`build_prompt` 前） |
| `agent.py` 原 prompt 段 | 替换为单行：`# Prompt 形状…见 mini_coding_agent.prompt` + 四个薄方法 |
| **新增** | `prompt.py` 模块 docstring |
| **删除** | 无用户注释批量删除；仅移除已迁走的函数体 |

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| agent 无大段 prefix/memory/history 拼装 | ✅ | 字符串逻辑均在 `prompt.py` |
| `/memory`、plan/skill 块与重构前一致 | ✅ | `test_memory_text_includes_plan_summary`、`test_memory_text_includes_loaded_skill_body`、`test_build_prefix_includes_skill_metadata_not_body` |
| history 去重行为不变 | ✅ | `test_history_text_deduplicates_*` |
| pytest + ruff | ✅ | 见下方 |
| feedback 含注释迁移说明 | ✅ | 本节 |
| 未迁 ask / run_tool | ✅ | 仅 touch prompt 相关 |

---

## 交付物

- `mini_coding_agent/prompt.py`（新建）
- `mini_coding_agent/agent.py`（委托 prompt）
- `docs/feedback/R3-PROMPT-EXTRACT.md`（本文件）

---

## 验证结果

```
$ python -m pytest -q
...........s.......................................................      [100%]
66 passed, 1 skipped in 45.48s

$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- 无。R4 可迁 `tool_*`、validate、`build_tools` 等于 `tools/`。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**
- **备注**: 独立复验 66 passed + ruff 绿。prompt 逻辑已迁至 `prompt.py`；agent 薄委托；注释已迁移。可派 R4。
