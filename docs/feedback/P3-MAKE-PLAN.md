# 子 Agent 回报：P3-MAKE-PLAN

## 元信息

- **TASK_ID**: P3-MAKE-PLAN
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

### 工具 `make_plan`

| 项 | 说明 |
|----|------|
| 注册 | `build_tools()` 中 `risky: False`，全 depth 可用（含 read_only 子 Agent） |
| Schema | `goal: str`（必填）、`context: str=''`（可选） |
| 执行 | `tool_make_plan` → **单次** `model_client.complete(planning_prompt)`，**无**内部 tool 循环 |
| 模块 | `mini_coding_agent/planning.py`：`build_planning_prompt`、`parse_plan_response`、`validate_plan`、`format_plan_tool_result` |

### Plan JSON 形状

```json
{
  "goal": "string",
  "steps": [
    {
      "id": "1",
      "title": "task-level step title",
      "acceptance": "how to verify done",
      "risky_hint": "optional: write_file | patch_file | run_shell"
    }
  ],
  "assumptions": ["string"],
  "out_of_scope": ["string"]
}
```

- 步数上限：`PLAN_MAX_STEPS = 12`（`validate_plan`）
- 非法 JSON / 缺字段 / 超步数 → 工具返回 `error: make_plan failed: ...`，**不**写 `memory.plan`
- 成功 → `plan_ok` + 人类可读摘要 + `<plan_json>...</plan_json>` 块

### Planning prompt 要点

- 角色：任务级规划助手（非函数级清单）
- 要求：**仅**返回 JSON 对象（示例 shape 内嵌于 prompt）
- 注入：`workspace.text()` 快照 + `goal` + 可选 `context`
- 解析：容忍 ` ```json ` 围栏；`extract_json_object` 取首尾 `{...}`

### Session / memory

- 成功 plan → `session["memory"]["plan"]`（dict）
- `memory_text()` 增加 `- plan:` 块（`plan_summary_text`：goal、步数、前 6 步标题）
- `reset()` 清空 `plan: None`
- 旧 session 无 `plan` 键 → `.get("plan")` 安全

### Prompt 引导（`build_prefix`）

- 多文件 / 含糊需求 / 用户要规划 → 先 `read_file`/`search` 再 `make_plan` 再 risky 工具
- `delegate` vs `make_plan` 分工说明
- 示例：`<tool>{"name":"make_plan","args":{"goal":"...","context":"..."}}</tool>`

### `--plan-first` enforcement

| 项 | 实现 |
|----|------|
| CLI | `argparse --plan-first` → `build_agent(..., plan_first=True)` |
| Agent 状态 | `self.plan_first`；每轮 `ask()` 开头 `_ask_plan_satisfied = False` |
| 门控点 | `_execute_tool_after_validation`：若 `plan_first` 且 `tool["risky"]` 且未 satisfied → 返回 error，**不**进入 approve/治理 |
| satisfied | 本轮 `ask()` 内 `tool_make_plan` 成功解析并写入 memory 后 `_ask_plan_satisfied = True` |
| 关闭时 | `plan_first=False`，与 Phase 2 一致，risky 可直接执行 |

**边界说明**：

- 门控在 **validate 之后、approve/治理之前**，属于产品行为，**不**改 Hook observe-only，**不**绕过 `approve()` / `_run_governed_file_tool`
- 仅约束 `write_file` / `patch_file` / `run_shell`（`risky: True`）
- **不**自动编排：无 step dispatch、无 plan 写盘

### 与 `delegate` 对比

| | `delegate` | `make_plan` |
|---|------------|-------------|
| 目的 | 只读调查子 Agent | 单次结构化任务拆分 |
| 模型调用 | 子 Agent 多步 tool 循环 | 工具内 **1 次** complete |
| risky | False | False |
| depth | 仅 `depth < max_depth` | 全 depth |
| 子 Agent | depth+1 **无** delegate | depth+1 **有** make_plan（read_only 可规划） |

---

## 契约对照表（struct/phase3.md §4）

| 场景 | 要求 | 满足 | 证据 |
|------|------|------|------|
| 模型返回非法 JSON | 明确错误；不写 memory.plan | ✅ | `test_make_plan_invalid_json_does_not_update_memory` |
| `goal` 为空 | validate 拒绝 | ✅ | `test_make_plan_rejects_empty_goal` |
| `--plan-first` 未 plan 即 risky | 拒绝并提示 | ✅ | `test_plan_first_blocks_risky_tool_until_make_plan`、`test_ask_plan_first_enforces_plan_before_write` |
| `--plan-first` 关闭 | 与 Phase 2 一致 | ✅ | `test_plan_first_off_allows_risky_without_plan` |
| plan 成功 | memory.plan 更新；prompt 可见 | ✅ | `test_make_plan_stores_structured_plan`、`test_memory_text_includes_plan_summary` |
| Hook 异常 | fail-open | ✅ | 未改 HookRegistry；`test_hook_fail_open_continues_tool_execution` 仍绿 |
| 子 Agent depth | 与 delegate 策略说明 | ✅ | `test_child_agent_has_make_plan_at_delegate_depth`（子 Agent 有 make_plan、无 delegate） |

---

## Done Definition 自证（struct/phase3.md §3）

| # | 交付 | 满足 | 证据 |
|---|------|------|------|
| 1 | `make_plan(goal, context?)`，`risky: False` | ✅ | `agent.build_tools`；`test_make_plan_stores_structured_plan` |
| 2 | 单次 `complete()` + planning prompt；无 tool 循环 | ✅ | `tool_make_plan`；`prompts[-1]` 以 planning assistant 开头 |
| 3 | 可解析 JSON + 步数 ≤12 | ✅ | `planning.validate_plan`；`test_validate_plan_rejects_too_many_steps`、`test_parse_plan_response_accepts_fenced_json` |
| 4 | `memory["plan"]` + `memory_text()` 摘要 | ✅ | `test_memory_text_includes_plan_summary` |
| 5 | `build_prefix` 规划引导规则 | ✅ | `agent.build_prefix` rules 段 |
| 6 | CLI `--plan-first` | ✅ | `cli.py`；门控见上文 |
| 7 | 走 `run_tool` / Hook / 治理不变 | ✅ | make_plan 经 `_invoke_tool_with_hooks`；治理测全绿 |
| 8 | pytest + FakeModelClient | ✅ | 见验证结果 |
| 9 | 回报本文档 | ✅ | — |

**明确未做**：auto-dispatch、`mark_step_done`、`.mini-coding-agent/plan.md`、benchmark、新 pip 依赖。

---

## Phase 1/2 回归说明

- 全量 `python -m pytest -q`：**53 passed, 1 skipped**（skip 为既有项）
- Phase 1 治理（diff/checkpoint/approve/rollback）、Phase 2 Hook（trace/shell_audit/fail-open）相关测试均未改动语义，全部通过
- `ruff check .`：All checks passed

---

## 交付物

| 路径 | 变更 |
|------|------|
| `mini_coding_agent/planning.py` | 新增：prompt、解析、校验、摘要 |
| `mini_coding_agent/agent.py` | `make_plan` 工具、memory.plan、`memory_text`、`build_prefix`、`plan_first` 门控 |
| `mini_coding_agent/cli.py` | `--plan-first` |
| `tests/test_mini_coding_agent.py` | Phase 3 测试（+11） |

---

## 验证结果

```
$ python -m pytest -q
...........s..........................................                   [100%]
53 passed, 1 skipped in 107.99s (0:01:47)

$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- Plan 质量依赖模型与 planning prompt，无 benchmark 打分
- `--plan-first` 仅约束**当前** `ask()` 轮次；跨轮 resume 不会自动继承 satisfied（每轮重新 `make_plan` 或关闭旗标）
- README 用户说明留待 **P3-DOCS**（本任务未改 README，符合 command 范围）

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**（2026-06-02）
- **备注**: 独立复验 `53 passed, 1 skipped` + ruff 绿。Done Definition §3 九条均满足；§9 README 按 OVERVIEW 拆至 **P3-DOCS**（合理）。`--plan-first` 门控在 validate 后、approve 前，契约清晰。已知取舍（每轮 ask 重置 satisfied、plan 质量无 benchmark）已记录在案，不挡通过。
