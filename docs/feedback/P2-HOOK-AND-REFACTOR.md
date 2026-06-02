# 子 Agent 回报：P2-HOOK-AND-REFACTOR

## 元信息

- **TASK_ID**: P2-HOOK-AND-REFACTOR
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

### Hook 架构

- **`HookRegistry`**（`mini_coding_agent/hooks.py`）：进程内注册 `pre_tool` / `post_tool` 回调；`emit_*` 对每条回调 **fail-open**（异常吞掉，主流程继续）。
- **`ToolHookContext`**：携带 `name`、`args`、`tool`、`result`、`success`、`duration_ms`、`risky`、`step`；Hook **只读**上下文，不改变 `run_tool` 返回值。
- **调用链**（校验通过后）：
  ```
  run_tool → validate_tool → repeated_tool_call?
    → _invoke_tool_with_hooks
         emit_pre
         _execute_tool_after_validation  (治理 / approve / tool["run"])
         emit_post (填充 success、duration)
  ```
- **未知工具 / 参数校验失败**：不触发 Hook（与契约「pre 在校验通过之后」一致）。

### 内置 Trace Hook

- **`ToolTraceHook`**（`mini_coding_agent/trace_hook.py`）：默认在 `MiniAgent(..., enable_trace_hook=True)` 时注册。
- **`pre_tool`**：分配 `step`（`len(tool_trace)+1`）。
- **`post_tool`**：向 `session["tool_trace"]` 追加 `{step, name, success, duration_ms, risky, created_at}`；**risky** 工具另写 `session["tool_audit"]`（仅 `args_keys`，不替代 `approve()`）。
- 禁用：`enable_trace_hook=False`（自定义 Hook 测试隔离）。

### 自定义 Hook API

```python
agent.register_hook("pre_tool", handler)
agent.register_hook("post_tool", handler)
```

### 委派（delegate）

- **父 Agent**：对 `delegate` 工具调用触发 **一对** pre/post（包裹整个子 Agent `ask`）。
- **子 Agent**：独立 `MiniAgent` 实例、独立 session、`enable_trace_hook=True`；子 session 内 `tool_trace` 记录子工具链，**不**合并进父 session（除非父 `delegate` 那一笔）。

### 重构

单文件 `mini_coding_agent.py`（~1389 行）拆为包 `mini_coding_agent/`，根目录保留 **CLI 薄入口** `mini_coding_agent.py`（`python mini_coding_agent.py` 不变）。

---

## 模块 map

| 模块 | 职责 |
|------|------|
| `mini_coding_agent.py`（根） | CLI 入口，`from mini_coding_agent.cli import main` |
| `mini_coding_agent/__init__.py` | 对外 re-export（兼容 `from mini_coding_agent import MiniAgent`） |
| `mini_coding_agent/agent.py` | `MiniAgent`：ask、run_tool、治理、工具实现、parse |
| `mini_coding_agent/hooks.py` | `HookRegistry`、`ToolHookContext` |
| `mini_coding_agent/trace_hook.py` | 内置 `ToolTraceHook` |
| `mini_coding_agent/util.py` | clip、diff、atomic_write、hash、`tool_result_success` |
| `mini_coding_agent/constants.py` | 全局常量 |
| `mini_coding_agent/workspace.py` | `WorkspaceContext` |
| `mini_coding_agent/session.py` | `SessionStore`、`CheckpointStore` |
| `mini_coding_agent/models.py` | `FakeModelClient`、`OllamaModelClient` |
| `mini_coding_agent/cli.py` | `build_welcome`、`build_agent`、`main` |
| `tests/test_mini_coding_agent.py` | Phase 1 回归 + Phase 2 Hook 新测 |

---

## 契约与 Done Definition 自证

### 可靠性契约（struct/07-phase2-reliability-contract §3）

| 场景 | 满足 | 证据 |
|------|------|------|
| Hook 回调抛异常 → fail-open | ✅ | `test_hook_fail_open_continues_tool_execution`；`HookRegistry._dispatch` |
| 无注册 Hook | ✅ | `enable_trace_hook=False` 且无 `register_hook` 时行为同 Phase 1（治理测仍绿） |
| 每次 run_tool 至多一对 pre/post | ✅ | `_invoke_tool_with_hooks` 单路径；`test_governed_tool_emits_single_hook_pair` |
| 治理 tool 语义不变 | ✅ | Phase 1 治理测试全绿；治理仍在 `_run_governed_file_tool` |
| Hook 不覆盖 Phase 1 字段 | ✅ | trace 用独立 `tool_trace` / `tool_audit` 键 |
| Phase 1 pytest 回归 | ✅ | 原 27 项 + 1 skip 保持；patch 目标改为 `mini_coding_agent.agent.atomic_write_text` |
| delegate 子 Agent Hook | ✅ | 子 Agent 独立 trace；父仅 `delegate` 一条；`test_delegate_child_has_independent_trace` |

### Done Definition §4.1 功能

| 指标 | 结果 | 证据 |
|------|------|------|
| 一套 pre_tool + post_tool | ✅ | `hooks.py` + `run_tool` 集成 |
| 进程内注册自定义回调 | ✅ | `register_hook`；`test_register_custom_hook_observes_tool` |
| 一个内置 trace Hook | ✅ | `ToolTraceHook`；`test_trace_hook_records_*` |
| 只观察 | ✅ | Hook 无 return 覆盖；不跳过 approve/治理 |
| fail-open | ✅ | `test_hook_fail_open_*` |
| session 可查 trace | ✅ | `session["tool_trace"]` |
| Phase 1 治理不变 | ✅ | diff/checkpoint/回滚/Git/`run_shell` 相关测试全绿 |

### Done Definition §4.2 工程

| 指标 | 结果 | 证据 |
|------|------|------|
| pytest 全绿 | ✅ | 见下方输出 |
| ruff | ✅ | 见下方输出 |
| 结构化重构 + 模块说明 | ✅ | 见「模块 map」 |
| CLI 兼容 | ✅ | 根 `mini_coding_agent.py` + `pyproject` script |
| README Extension | ⏳ | 由 **P2-DOCS** 任务交付（本任务未改 README） |

### Phase 1 回归说明

以下测试直接锁定 Phase 1 治理语义未退化：

- `test_approval_denied_leaves_file_unchanged`
- `test_write_file_records_diff_metadata`
- `test_ask_records_governance_metadata_in_history`
- `test_write_failure_rolls_back_new_file`
- `test_patch_failure_restores_original_content`
- `test_restore_skips_when_file_modified_externally`
- `test_approve_shows_diff_not_raw_json`
- `test_git_dirty_warning_shown_on_approval`
- `test_run_shell_approval_unchanged`
- `test_invalid_risky_tool_does_not_prompt_for_approval`

---

## 交付物

- `mini_coding_agent/` 包（8 模块 + `agent.py`）
- 根 `mini_coding_agent.py` CLI 入口
- `pyproject.toml`：`packages.find` 替代 `py-modules`
- `tests/test_mini_coding_agent.py`：+7 Hook 测，治理 patch 路径更新

---

## 验证结果

```
python -m pytest -q
34 passed, 1 skipped in ~47s

python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- **README**：Extension & Observability 章节待 P2-DOCS。
- **测试 patch 路径**：治理失败回滚测试须 patch `mini_coding_agent.agent.atomic_write_text`（实现已迁包内）。
- **子 Agent 与父共享 `FakeModelClient`**：集成测试须为子 Agent 预留足够 `outputs`（见 `test_delegate_child_has_independent_trace`）。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过** — P2-HOOK-AND-REFACTOR 可结项；可派发 P2-DOCS → P2-REVIEW。
- **备注**:
  - 独立复验（2026-06-01）：`34 passed, 1 skipped`；`ruff check .` 全绿。
  - Done Definition §4.1 功能指标全部满足；§4.2 中 README 按任务分工留给 P2-DOCS（合理）。
  - 可靠性契约 §3 逐项与 feedback 一致；未知工具/校验失败不触发 Hook 符合契约。
  - delegate 策略（父仅包裹 delegate 一对、子独立 trace）已在 feedback 说明且有用例覆盖。
  - 无 Blocker。
