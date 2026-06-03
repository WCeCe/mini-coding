# 子 Agent 回报：OPT-ASK-TIMING

---

## 元信息

- **TASK_ID**: OPT-ASK-TIMING
- **状态**: 完成

---

## 方案摘要（IMPLEMENT 必填）

新增模块 `mini_coding_agent/ask_timing.py`，包含：

| 符号 | 职责 |
|------|------|
| `AskTimingCollector` | 单次 `ask()` 内存收集器：按序追加 `llm` / `tool` 事件，结束时 `build_record()` |
| `AskTimingHook` | 注册于 `HookRegistry`（`pre_tool` / `post_tool`）；活跃 ask 期间将 `ctx.duration_ms` 写入 collector，步序复用 `ToolTraceHook` 的 `ctx.step`（trace 关闭时自行计数） |
| `append_ask_timing_log()` | fail-open 追加一行 JSON 到 `<repo>/.mini-coding-agent/logs/<session_id>.jsonl` |

**主循环改动**（`agent.py` · `ask()`）：

1. 每条用户消息递增 `session["ask_count"]` 作为稳定 `ask_id`。
2. 创建 `AskTimingCollector`，设置 `agent._ask_timing`；`finally` 中落盘并清空。
3. 每次 iteration：`perf_counter()` 包裹 `prompt()` → `complete_with_wait_display()` → `parse()` → 按 outcome 记一条 `llm`（`tool` / `retry` / `final`）。
4. 步数/attempt 上限退出时 `mark_last_llm_stop()` 将**最近一条** `llm` 的 outcome 改为 `stop`。
5. `AskTimingHook` 在 `__init__` 末尾始终注册（与 `enable_trace_hook` 无关）。

**方案 A**：`make_plan` / `delegate` 内部 `complete()` 不计独立 `llm` 事件，时间计入对应 `tool` 的 Hook 边界耗时。

**记录 JSON 示例**（单行 append）：

```json
{
  "session_id": "20260603-135856-a5956b",
  "ask_id": 1,
  "user_message": "你好",
  "total_ms": 12.34,
  "events": [
    {"kind": "llm", "attempt": 1, "duration_ms": 0.13, "outcome": "final"}
  ],
  "created_at": "2026-06-03T05:58:56.270772+00:00"
}
```

**异常行为**：`ask()` 内 `finally` 双层 fail-open（`append_ask_timing_log` 内部 + `agent.ask` 外层 try/except）；模型 `complete()` 抛错时仍写入已收集的部分 events 与 `total_ms`。`run_tool()` 单独调用（非 ask 主循环）不写 jsonl。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据（测试名 / 行为说明） |
|------|----------|---------------------------|
| 纯对话 ask（0 tool）：1 条 `llm` + `total_ms` | ✅ | `test_ask_timing_pure_dialog_records_single_llm` |
| tool 路径：`llm` / `tool` 交替 | ✅ | `test_ask_timing_tool_path_alternates_llm_and_tool` |
| tool `duration_ms` 与 `tool_trace` 一致 | ✅ | `test_ask_timing_tool_duration_matches_tool_trace`（误差 < 0.01 ms） |
| `make_plan` 仅 1 条 `tool`，无嵌套 `llm` | ✅ | `test_ask_timing_make_plan_single_tool_no_nested_llm` |
| 多轮 ask 同 session jsonl append | ✅ | `test_ask_timing_multiple_asks_append_jsonl`（`ask_id` 1→2） |
| 写盘 fail-open | ✅ | `test_ask_timing_write_fail_open`；`append_ask_timing_log` 内部亦 try/except |
| 校验失败未进 Hook 无 tool 事件 | ✅ | `test_ask_timing_validation_error_no_tool_event` |
| 步数上限 `stop` outcome | ✅ | `test_ask_timing_stop_outcome_on_step_limit` |
| 新增 pytest；全量绿；ruff 通过 | ✅ | 79 passed, 1 skipped；ruff All checks passed |
| 无新 pip 依赖 | ✅ | 仅用标准库 `json` / `perf_counter` |

---

## 交付物

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/ask_timing.py` | 新建：Collector、Hook、jsonl 落盘 |
| `mini_coding_agent/agent.py` | `ask()` 计时 + Hook 注册 + `ask_count` |
| `tests/test_mini_coding_agent.py` | +8 个 ask_timing 测试 |
| `docs/feedback/OPT-ASK-TIMING.md` | 本回报 |

---

## 验证结果

```
$ python -m pytest tests/test_mini_coding_agent.py -q --tb=no
...........s............................................................ [ 90%]
........                                                                 [100%]
79 passed, 1 skipped in 52.65s

$ python -m ruff check mini_coding_agent/ tests/
All checks passed!
```

---

## 风险与未解决问题

- **`ask_count` 存于 session JSON**：resume 后继续递增，与 jsonl 行序一致；旧 session 无该字段时从 0 起算。
- **未单独计时 `record()` / session 落盘**：符合 MVP 口径。
- **无 CLI 关闭旗标**：任务不要求；默认始终写 log。
- **delegate 子 Agent**：子 session 独立 jsonl；父 ask 仅见一条 `delegate` tool 事件（方案 A）。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: 通过
- **备注**: 主 Agent 独立复跑 pytest（79 passed, 1 skipped）与 ruff；方案 A（llm/tool 两档、make_plan 不拆嵌套 llm）、jsonl append、fail-open 均符合 `OPT-ASK-TIMING` 契约。log 路径：`<repo>/.mini-coding-agent/logs/<session_id>.jsonl`。
