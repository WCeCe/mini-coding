# 子 Agent 回报：R4-TOOLS-EXTRACT

## 元信息

- **TASK_ID**: R4-TOOLS-EXTRACT
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

将工具注册、校验、沙箱、各 `tool_*` 实现及 `run_tool` 管道迁至 **`mini_coding_agent/tools/`** 包；`MiniAgent` 收敛为编排器（初始化、ask 主循环、Hook 接线、Skills session 辅助、薄委托）。

**run 管道边界（与 R2/R3 衔接）**

```
run_tool (tools/runtime.py)
  → validate_tool / repeated_tool_call / tool_example (tools/validators.py)
  → invoke_tool_with_hooks (Hook 仍在 agent.hook_registry)
  → execute_tool_after_validation
       → [plan-first 门控] — agent.plan_first / _ask_plan_satisfied
       → write_file|patch_file → governance.run_governed_file_tool(agent, …)
       → 其他 risky → agent.approve → governance.approve
       → tool["run"](args) → implementations.tool_*
```

write/patch **无** `run` 注册项，**不**在 `implementations.py` 直写。

---

## 最终模块 map

| 模块 | 职责 |
|------|------|
| `mini_coding_agent/agent.py` | **编排器**：`__init__`、session、ask、record/note_tool、Hook 注册、Skills 加载/reset、薄委托 |
| `mini_coding_agent/protocol.py` | 模型输出 parse / XML / retry |
| `mini_coding_agent/governance.py` | Phase 1 diff / checkpoint / approve / 回滚 |
| `mini_coding_agent/prompt.py` | build_prefix / memory_text / history_text / build_prompt |
| `mini_coding_agent/tools/__init__.py` | 包导出 |
| `mini_coding_agent/tools/sandbox.py` | `resolve_path`、`path_is_within_root` |
| `mini_coding_agent/tools/registry.py` | `build_tools(agent)` 注册表 |
| `mini_coding_agent/tools/validators.py` | `validate_tool`、`tool_example`、`repeated_tool_call` |
| `mini_coding_agent/tools/runtime.py` | `run_tool`、`invoke_tool_with_hooks`、`execute_tool_after_validation` |
| `mini_coding_agent/tools/implementations.py` | `tool_list_files` … `tool_load_skill`（无 write/patch 直写） |
| `planning.py` / `skills.py` / `hooks/` | 既有 Phase 3–4 / Phase 2 模块，未改契约 |

### 六大组件可指认

| 组件 | 模块 |
|------|------|
| 1 协议解析 | `protocol.py` |
| 2 Prompt 形状 | `prompt.py` |
| 3 结构化工具 | `tools/*` |
| 4 上下文压缩 | `prompt.history_text` + `util.clip` |
| 5 Session 记忆 | `agent.ask` / record / note_tool + `prompt.memory_text` |
| 6 变更治理 | `governance.py` |

---

## agent 行数

| 文件 | R3 后 | R4 后 |
|------|-------|-------|
| `agent.py` | ~741 | **~337** |

目标 ~350–450 行：**满足**（略低于下限，因 R1–R3 已迁出大量逻辑）。

**tools/ 新增行数**

| 文件 | 行数 |
|------|------|
| `sandbox.py` | ~25 |
| `registry.py` | ~72 |
| `validators.py` | ~111 |
| `runtime.py` | ~84 |
| `implementations.py` | ~148 |
| `__init__.py` | ~16 |

---

## 注释迁移说明

| 原位置（`agent.py`） | 处置 |
|----------------------|------|
| `#搭建tools字典` 及 build_tools 内各工具行注释 | **迁入** `tools/registry.py` |
| run_tool / invoke / execute 及 plan-first、治理分支注释 | **迁入** `tools/runtime.py` |
| `repeated_tool_call` / `tool_example` / `validate_tool` 及内部注释 | **迁入** `tools/validators.py` |
| `path_is_within_root` / `path` | **迁入** `tools/sandbox.py`（逻辑等价 `resolve_path`） |
| `# 具体的工具实现` 及各 `tool_*` 注释 | **迁入** `tools/implementations.py` |
| delegate / make_plan / load_skill 段标题与注释 | **迁入** `implementations.py` 对应函数 |
| `agent.py` 原工具大段 | 替换为 `# 工具注册、validate、run 管道见 mini_coding_agent.tools` + `run_tool` 一行委托 |
| **保留在 agent** | ask、session、Skills、__init__ 等处用户注释未动 |
| **删除** | 无批量删注释；仅迁走函数体 |

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| agent 显著瘦身 | ✅ | ~337 行 |
| write/patch 只走 governance | ✅ | registry 无 run；runtime 分支 |
| Phase 1–4 行为不变 | ✅ | 66 passed |
| Hook / plan-first / delegate / skills | ✅ | 既有用例全绿 |
| pytest + ruff | ✅ | 见下方 |
| feedback 含模块 map、行数、注释说明 | ✅ | 本节 |

---

## 交付物

- `mini_coding_agent/tools/`（新建包，5 模块 + `__init__.py`）
- `mini_coding_agent/agent.py`（编排器）
- `tests/test_mini_coding_agent.py`（subprocess patch 路径 2 处）
- `docs/feedback/R4-TOOLS-EXTRACT.md`（本文件）

---

## 验证结果

```
$ python -m pytest -q
...........s.......................................................      [100%]
66 passed, 1 skipped in 48.46s

$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- `tool_delegate` 内 lazy import `MiniAgent` 避免循环依赖；行为与迁前一致。
- ToolSpec 三处合一（struct §7）留待后续，本次未做。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**
- **备注**: 独立复验 66 passed + ruff 绿；`agent.py` 约 308 行；`tools/` 包齐全；write/patch 仅 governance。可派 REFACTOR-REVIEW。
