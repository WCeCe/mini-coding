# 任务单：OPT-ASK-TIMING

## 元信息

- **TASK_ID**: OPT-ASK-TIMING
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P1
- **可以写代码**: 是
- **性质**: 横切可观测优化（非新 Phase）；与 Phase 2 Hook 互补，不替代 `tool_trace`

---

## 背景

Phase 2 Hook 仅在 `run_tool` 边界统计 `duration_ms` 并写入 session `tool_trace`。**主循环 LLM**（含 prompt 拼装 + `complete` + `parse`）无计时；纯对话（如「你好」）时 `tool_trace` 为空，无法回答「这次 ask 慢在哪里」。

用户已对齐：**两档粒度（LLM / tool）+ 方案 A**（工具内嵌 LLM 不单独拆条，如 `make_plan`、`delegate` 只记一条 tool 总耗时）。

---

## 目标

每次 `ask()` 结束时，将本轮耗时摘要 **append 一条 JSON** 到磁盘 log，事件序列为交替的 **`llm`** 与 **`tool`** 条目，便于事后分析「时间花在模型还是工具」。

---

## 计时口径（方案 A · 必须遵守）

### `llm` 事件

- **范围**：主循环内一次 iteration 中，`prompt()` → `complete_with_wait_display()`（或等价 complete 包装）→ `parse()` → 判定 outcome。
- **一条 iteration = 一条 `llm`**，不论 outcome 是 `tool` / `retry` / `final` / 步数用尽前的最后一次。
- **不含** `make_plan` / `delegate` 等 **工具内部** 的 `complete()`（那些时间计入对应 **tool** 总耗时）。

建议字段（可微调，须在 feedback 自洽）：

```json
{"kind": "llm", "attempt": 1, "duration_ms": 182000, "outcome": "final"}
```

`outcome` 示例：`tool` | `retry` | `final` | `stop`（步数/attempt 上限退出）。

### `tool` 事件

- **范围**：与 Phase 2 Hook 一致——`invoke_tool_with_hooks` 的 `pre_tool`～`post_tool` 整段 `duration_ms`（含 validate 之后路径、治理、审批等待、`make_plan` 内 LLM、`delegate` 整段子 ask 等）。
- **一条 tool 调用 = 一条 `tool`**；与 session `tool_trace` 步序应对齐（同一次调用同一 `step` 或同序）。

建议字段：

```json
{"kind": "tool", "step": 1, "name": "read_file", "duration_ms": 120, "success": true}
```

### 不计时（MVP 不要求）

- `record()` / session 落盘
- spinner / `wait_display` 纯 UI
- 校验失败且 **未进入** `invoke_tool_with_hooks` 的路径（未知工具、validate 失败）——可在 `llm` outcome 为 `tool` 时通过 tool 缺失或 success=false 体现，不强制单独事件

### ask 汇总

每条 log 记录须含：

- `session_id`、`ask` 序号或 `ask_id`（子 Agent 定，须稳定可排序）
- `user_message`（可 clip，如 ≤300 字符）
- `total_ms`（本次 `ask()` 墙钟总耗时）
- `events`：按发生顺序的 `llm` / `tool` 数组
- `created_at`（ISO 或现有 `now()` 格式，与项目一致）

---

## Log 落盘

- **路径**：`<repo_root>/.mini-coding-agent/logs/<session_id>.jsonl`（每 session 一个文件，**append** 一行 JSON / ask）
- **目录**：不存在则创建；写入 fail-open（失败不拖垮 `ask()` 主流程）
- **默认始终开启**；本任务 **不要求** CLI 关闭旗标（与 OPT-WAIT-DISPLAY 一致）

---

## 约束

- 见 [`struct/01-vision-and-roadmap.md`](../struct/01-vision-and-roadmap.md) 铁律：标准库优先、新行为 pytest（`FakeModelClient`）、保留用户注释、新增代码适量注释
- **不**改 tool 协议、治理语义、Hook observe-only 契约
- **不**拆 `make_plan` / `delegate` 内部 LLM 为独立 `llm` 事件（方案 A）
- **不**引入新 pip 依赖
- 与现有 `tool_trace` **并存**；本任务 log 按 **ask** 分组，不要求重构 `tool_trace`
- 子 Agent **一次完成**实现 + pytest + ruff + 完整回报

---

## 交付物

1. 代码：`mini_coding_agent/`（新模块或扩展现有模块由子 Agent 定）、`tests/`
2. 回报：[`feedback/OPT-ASK-TIMING.md`](../feedback/OPT-ASK-TIMING.md)

---

## 验收标准

- [x] 纯对话 ask（0 tool）：log 含 **1 条 `llm`** + `total_ms`，可解释「你好很慢」类场景
- [x] tool 路径：log 中 `llm` 与 `tool` 交替，tool 的 `duration_ms` 与 Hook `tool_trace` 同次调用一致（允许四舍五入误差）
- [x] `make_plan`：仅 **1 条 `tool`**（含内部 LLM），无额外 `llm` 表内嵌条目
- [x] 多轮 ask：同一 session 的 jsonl **append** 多行，可区分不同 ask
- [x] 写盘 fail-open；`ask()` 失败/异常时行为在 feedback 说明
- [x] 新增 pytest；全量 pytest 仍绿；ruff 通过
- [x] 无新 pip 依赖

---

## 参考资料

- [`struct/phase2.md`](../struct/phase2.md) §5 — ask 结束汇总为后续方向
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) — `ask()` 主循环、Hook 链
- [`mini_coding_agent/agent.py`](../../mini_coding_agent/agent.py)
- [`mini_coding_agent/tools/runtime.py`](../../mini_coding_agent/tools/runtime.py)
- [`mini_coding_agent/hooks/trace_hook.py`](../../mini_coding_agent/hooks/trace_hook.py)
- [`mini_coding_agent/wait_display.py`](../../mini_coding_agent/wait_display.py)

---

*主 Agent 下达 · 方案 A · 实现路径由子 Agent 自定*
