# 子 Agent 回报：R2-GOVERNANCE-EXTRACT

## 元信息

- **TASK_ID**: R2-GOVERNANCE-EXTRACT
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

将 Phase 1 变更治理整段迁至 **`mini_coding_agent/governance.py`**，并移除 `write_file` / `patch_file` 的 dead path 直写实现。

**调用链（不变）**

```
run_tool → validate → repeated_check → Hook
  → _execute_tool_after_validation
       → [plan-first 门控]
       → write_file|patch_file → governance.run_governed_file_tool(agent, …)
       → 其他 risky → governance.approve(…) → tool["run"](args)
```

- **`governance.py`**：`run_governed_file_tool`、`proposed_file_content`、`restore_checkpoint`、`approve`（模块级函数；`run_governed_file_tool` 接收 `agent` 以访问 path/root/workspace/checkpoint_store/session）。
- **`agent.py`**：`run_governed_file_tool(self, …)` 委托；保留 `approve` / `_restore_checkpoint` 薄包装（测试与外部 API 兼容）；plan-first / Hook 门控位置未动。
- **dead path**：删除 `tool_write_file` / `tool_patch_file`；`build_tools` 中两工具不再注册 `"run"`。

---

## 模块 map

| 模块 | 职责（R2 后） |
|------|----------------|
| `mini_coding_agent/governance.py` | **新建**。diff、checkpoint、approve、回滚、proposed content |
| `mini_coding_agent/agent.py` | 编排：委托 governance；validate / Hook / plan-first 仍在 agent |
| `mini_coding_agent/protocol.py` | R1 不变 |
| `tests/test_mini_coding_agent.py` | 2 处 patch 路径：`agent.atomic_write_text` → `governance.atomic_write_text` |

**行数**：`agent.py` ~992 → ~873（−119）；`governance.py` 新建 ~133 行。

---

## dead path 处理说明

| 项 | 处置 |
|----|------|
| `MiniAgent.tool_write_file` | **删除**（~6 行直写，经 `run_tool` 不可达） |
| `MiniAgent.tool_patch_file` | **删除**（~15 行直写，经 `run_tool` 不可达） |
| `build_tools` 中 `"run": self.tool_write_file` / `tool_patch_file` | **移除**；schema / risky / description 保留 |
| 实际写盘路径 | **唯一**：`_execute_tool_after_validation` → `run_governed_file_tool` → diff → approve → checkpoint → `atomic_write_text` |

**理由**：Phase 1 起 `run_tool` 已对 write/patch bypass 至治理链；`tool_*` 直写从未被调用，属冗余 dead path。删除后若误走 `tool["run"]` 会 KeyError——write/patch 在 validate 后已被 governance 分支拦截，不会落入该路径。

---

## 注释迁移说明

| 原位置（`agent.py`） | 处置 |
|----------------------|------|
| `# 处理写文件和patch文件的治理主流程` 及 `_run_governed_file_tool` 内全部注释 | **迁入** `governance.run_governed_file_tool` |
| `#如果是write_file…` → `_proposed_file_content` | **迁入** `governance.proposed_file_content` |
| `#回滚` 及 `_restore_checkpoint` 内注释 | **迁入** `governance.restore_checkpoint` |
| `#是否允许使用能修改…` → `approve` 及 diff/EOF 分支注释 | **迁入** `governance.approve` |
| `# 这里调用_run_governed_file_tool，不走传统的write_file两个工具了` | **改写**为指向 `governance.run_governed_file_tool` |
| plan-first 注释中的 `_run_governed_file_tool` | **改写**为 `governance.run_governed_file_tool` |
| `build_tools` 中 write/patch 的 `#content…` / `#精确文本替换…` | **保留**；**新增**「执行经治理链，无直写 run」 |
| `agent.py` 原治理段 | 替换为 `approve` / `_restore_checkpoint` 薄包装 + 单行见 governance 注释 |
| **新增** | `governance.py` 模块 docstring |
| **删除** | 无独立用户注释；`tool_write_file`/`tool_patch_file` 函数体随 dead path 整段删除（函数上无块注释） |

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| 治理逻辑集中在一模块 | ✅ | `governance.py` 含 diff/checkpoint/approve/rollback |
| agent 无大段治理实现 | ✅ | 仅委托 + 薄包装 |
| write/patch 无 dead `tool_*` 注册 | ✅ | `build_tools` 无 `run`；`tool_write_file`/`tool_patch_file` 已删 |
| Phase 1 治理测试全绿 | ✅ | `test_approve_shows_diff_not_raw_json`、`test_write_failure_rolls_back_new_file`、`test_patch_failure_restores_original_content`、`test_restore_skips_when_file_modified_externally` 等 |
| plan-first / Hook 回归 | ✅ | `test_plan_first_blocks_risky_until_make_plan`、`test_governed_tool_emits_single_hook_pair` 等仍绿 |
| 全量 pytest + ruff | ✅ | 见下方 |
| feedback 含 dead path + 注释迁移 | ✅ | 本节 |

---

## 交付物

- `mini_coding_agent/governance.py`（新建）
- `mini_coding_agent/agent.py`（委托治理、移除 dead path）
- `tests/test_mini_coding_agent.py`（patch 路径 2 处）
- `docs/feedback/R2-GOVERNANCE-EXTRACT.md`（本文件）

---

## 验证结果

```
$ python -m pytest -q
...........s.......................................................      [100%]
66 passed, 1 skipped in 42.14s

$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- 无。R3 可继续迁 prompt（`build_prefix` / memory / history）；R4 迁其余 `tool_*` 与 validate。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**
- **备注**: 独立复验 66 passed + ruff 绿。`governance.py` 集中治理；write/patch 无 `run`、无 `tool_*` dead path；注释已迁移。`02-codebase-reference` 待 REFACTOR-REVIEW 统一更新。可派 R3。
