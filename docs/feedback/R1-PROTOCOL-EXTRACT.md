# 子 Agent 回报：R1-PROTOCOL-EXTRACT

## 元信息

- **TASK_ID**: R1-PROTOCOL-EXTRACT
- **TASK_TYPE**: IMPLEMENT（纯结构迁移）
- **状态**: 完成

---

## 方案摘要

将 `MiniAgent` 上的模型输出协议解析逻辑整段迁至 **`mini_coding_agent/protocol.py`**，以**纯函数**实现，不依赖 `MiniAgent` 实例。

- **`ask()`** 内 `self.parse(raw)` 改为 `from mini_coding_agent.protocol import parse` 后直接调用 `parse(raw)`。
- **`agent.py`** 删除 6 个 `@staticmethod`（`parse`、`retry_notice`、`parse_xml_tool`、`parse_attrs`、`extract`、`extract_raw`），原位置留一行指向注释。
- **未改** governance、prompt、tool 实现、Phase 1–4 逻辑；`tests/` 无需调整（现有用例经 `ask()` 间接覆盖 parse 路径）。

---

## 模块 map

| 模块 | 职责（R1 后） |
|------|----------------|
| `mini_coding_agent/protocol.py` | **新建**。`parse` / `parse_xml_tool` / `parse_attrs` / `extract` / `extract_raw` / `retry_notice` |
| `mini_coding_agent/agent.py` | 编排：`ask()` 调用 `protocol.parse`；治理 / prompt / 工具仍在本文件（R2–R4 待迁） |
| `tests/test_mini_coding_agent.py` | 无改动；JSON tool、XML tool、retry、final 路径仍经 `FakeModelClient` + `ask()` 覆盖 |

**行数**：`agent.py` ~1111 → ~992（−119）；`protocol.py` 新建 ~123 行。

---

## 注释迁移说明

| 原位置（`agent.py`） | 处置 |
|----------------------|------|
| `#解析模型返回的结果` 及 `parse()` 内全部行内注释（tool/final 优先级、JSON 反序列化、args 校验、兜底纯文本等） | **整段迁入** `protocol.py` 对应函数 |
| `#（属于parse）用于生成…` → `retry_notice` | **迁入** `protocol.py` |
| `#（属于parse）解析XML格式…` → `parse_xml_tool` 及 attrs/body/白名单 key 注释 | **迁入** `protocol.py` |
| `#（属于parse）parse_attrs…` | **迁入** `protocol.py` |
| `#（属于parse）从文本中截取出…`（`extract` / `extract_raw` 各一条） | **迁入** `protocol.py` |
| `agent.py` 原 parse 段 | 替换为单行：`# 模型输出协议解析（parse / XML / retry）见 mini_coding_agent.protocol` |
| **新增** | `protocol.py` 模块 docstring：说明纯函数、无 MiniAgent 依赖 |
| **删除** | 无用户注释被删；仅移除已迁走的函数体（逻辑随块迁出，非批量删注释） |

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| 协议解析不在 `agent.py` 重复实现 | ✅ | `agent.py` 无 `def parse`；仅 `import parse` + 一行见 protocol 注释 |
| 全量 pytest + ruff | ✅ | 见下方验证输出 |
| 无行为变更（parse/retry/final/tool JSON·XML） | ✅ | `test_agent_retries_after_empty_model_output`、`test_agent_retries_after_malformed_tool_payload`、`test_agent_accepts_xml_write_file_tool` 等仍绿 |
| feedback 含注释迁移说明与模块 map | ✅ | 本节 |
| 未改 Phase 1–4 治理/Hook/plan/skill | ✅ | 仅 touch `agent.py`（import + ask 一行 + 删 parse 段）与新建 `protocol.py` |

---

## 交付物

- `mini_coding_agent/protocol.py`（新建）
- `mini_coding_agent/agent.py`（委托 `protocol.parse`，移除 static parse 段）
- `docs/feedback/R1-PROTOCOL-EXTRACT.md`（本文件）

---

## 验证结果

```
$ python -m pytest -q
...........s.......................................................      [100%]
66 passed, 1 skipped in 42.91s

$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- 无。R2 可继续迁 governance；当前 `write_file`/`patch_file` dead path  intentionally 未动。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**
- **备注**: 独立复验 `66 passed, 1 skipped` + ruff 绿。`protocol.py` 纯函数、注释已迁移；agent 无重复 parse 实现。可派 R2。
