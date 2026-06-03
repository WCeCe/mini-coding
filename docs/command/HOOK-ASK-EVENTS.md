# 任务单：HOOK-ASK-EVENTS

## 元信息

- **TASK_ID**: HOOK-ASK-EVENTS
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **性质**: Hook 架构扩展 + OPT-ASK-TIMING 归位（**一次做完，不拆阶段**）
- **替代/收敛**: 根目录 `mini_coding_agent/ask_timing.py` 及 `agent.ask()` 内手写计时/落盘逻辑

---

## 背景

OPT-ASK-TIMING 功能已验收（jsonl、方案 A 口径），但实现 **违反 Phase 2 Hook 架构**：

- 模块在包根 `ask_timing.py`，未进 `hooks/`
- `AskTimingHook` 在 `agent.__init__` 单独注册，绕过 `register_builtin_hooks` / `hooks.yaml`
- LLM 计时与 jsonl 落盘写在 `agent.ask()`，非 Hook 触发点
- 使用 `agent._ask_timing` 私有耦合

用户要求：**先补 ask/llm 触发点，再让 ask timing 作为正统内置 Hook 实现**；**不拆分两阶段，一次交付**。

---

## 目标

1. **扩展 Hook 事件模型**：在 observe-only、fail-open 契约下，增加 ask / llm 边界事件。
2. **`agent.ask()` 只 emit**，不写 `record_llm`、不 `append_ask_timing_log`、不维护 `_ask_timing`。
3. **`AskTimingHook` 迁入 `hooks/`**，经 `builtin.py` + `HookConfig` + `hooks.yaml` 装配；**行为与 OPT-ASK-TIMING 一致**（jsonl 路径、字段、方案 A）。
4. **`register_hook` 支持新事件**，便于用户后续自定义观察逻辑。
5. **删除**根目录 `mini_coding_agent/ask_timing.py`。

---

## Hook 架构（必须遵守）

### 目录

```
mini_coding_agent/hooks/
├── registry.py           # 扩展：AskHookContext、LlmHookContext、emit_pre/post_ask、emit_pre/post_llm
├── hook_config.py        # + ask_timing: bool
├── builtin.py            # + AskTimingHook 装配
├── ask_timing_hook.py    # Collector + jsonl 落盘 + Hook 类（从根目录迁入）
├── trace_hook.py         # 不变语义
├── trace_display_hook.py
├── shell_audit_hook.py
├── hooks.yaml.example    # 文档化 ask_timing 键
└── __init__.py           # 按需导出
```

**禁止**：在 `mini_coding_agent/` 包根新增 `*_hook.py` 或观察类模块。

### 事件与触发点

| 事件 | 触发位置 | 计时责任 |
|------|----------|----------|
| `pre_ask` / `post_ask` | `agent.ask()` 入口 / `finally`（含异常路径） | registry 或 Hook 内 `perf_counter`；`post_ask` 携带 ask 总耗时 |
| `pre_llm` / `post_llm` | 主循环每轮：`prompt` 前 / `parse` 后 | registry 在 pre/post 间算 `duration_ms`；`post_llm` 带 `attempt`、`outcome` |
| `pre_tool` / `post_tool` | 现有 `invoke_tool_with_hooks` | **保持现有语义** |

**`outcome`（post_llm）**：`tool` | `retry` | `final` | `stop`（步数/attempt 上限时由 ask 循环在 emit post_llm 时传入，或在 post_ask 前统一 mark——须在 feedback 说明且与现测一致）。

**方案 A（不变）**：`make_plan` / `delegate` 内部 `complete()` **不**产生独立 `llm` 事件；时间仍在 `post_tool` 的 `duration_ms` 内。

### Context 设计（子 Agent 自定，须满足）

- **`AskHookContext`**：至少 `agent`、`ask_id`、`user_message`；可含共享 collector 或 events 列表供 `AskTimingHook` 写入。
- **`LlmHookContext`**：至少 `agent`、`ask_ctx`（或 back-ref）、`attempt`；post 时 `duration_ms`、`outcome`。
- **`ToolHookContext`**：保持兼容；现有内置 Hook **不得行为回归**。

### 装配与配置

- `register_builtin_hooks` **唯一**内置注册入口；移除 `agent.__init__` 里对 `AskTimingHook` 的直接构造。
- `HookConfig.ask_timing: bool = True`；`hooks.yaml` → `builtin_hooks.ask_timing`；CLI 可选 `--no-ask-timing`（与 `--no-session-trace` 同级，**可选**；若不做 CLI，yaml + `enable_trace_hook=False` 须能关闭）。
- **`enable_trace_hook=False`**：不注册**任何**内置 Hook（含 AskTiming），与测试隔离一致。

### 契约（Phase 2 延续）

- Hook **只观察**，fail-open（`_dispatch` 吞异常）
- 不阻断 approve、治理、模型调用
- jsonl 写盘 fail-open（`post_ask` 内）

---

## AskTimingHook 职责（归位后）

- 订阅：`post_llm`（记 llm 事件）、`post_tool`（记 tool 事件，用 `ctx.duration_ms` + `ctx.step`）、`post_ask`（`build_record` + append jsonl）
- 删除对 `agent._ask_timing` 的依赖；collector 生命周期绑在 `AskHookContext`（或等价机制）
- jsonl 路径与格式 **与 OPT-ASK-TIMING 一致**：
  - `<repo>/.mini-coding-agent/logs/<session_id>.jsonl`
  - 字段：`session_id`、`ask_id`、`user_message`、`total_ms`、`events`、`created_at`
- `ask_id`：仍用 `session["ask_count"]` 递增（resume 兼容）

---

## `agent.ask()` 目标形态（示意，非逐步实现清单）

```
递增 ask_count → 构建 AskHookContext → emit pre_ask
try:
  while ...:
    emit pre_llm → prompt → complete → parse → emit post_llm(outcome=...)
    if tool: run_tool(...)   # 已有 post_tool
    ...
finally:
  emit post_ask
```

**不得**在 ask 内直接调用已删除的 `append_ask_timing_log` / `AskTimingCollector.record_*`（除非 collector 仅由 Hook 内部使用且通过 context 传递）。

---

## 约束

- 铁律：标准库优先、pytest（FakeModelClient）、保留用户注释、中文用户可见文案
- **无新 pip 依赖**
- 现有 OPT-ASK-TIMING 的 **8 个测试**须通过（可改 import/monkeypatch 路径，不断言语义）
- 现有 Phase 2 Hook 测试（trace、custom hook、fail-open、yaml）**不得回归**
- 更新 `hooks.yaml.example`；可选更新 README Extension 小节一句（非必须，若改须准确）

---

## 交付物

1. 代码：`hooks/*`、`agent.py`；**删除** `mini_coding_agent/ask_timing.py`
2. 测试：`tests/test_mini_coding_agent.py`（增补 registry 新事件测试若需要）
3. 回报：[`feedback/HOOK-ASK-EVENTS.md`](../feedback/HOOK-ASK-EVENTS.md)（方案摘要、事件模型图、与 OPT-ASK-TIMING 差异、验收自证、pytest/ruff 全文）

---

## 验收标准

- [x] `HookRegistry.register` 接受 `pre_ask` / `post_ask` / `pre_llm` / `post_llm`；未知事件仍报错
- [x] `agent.register_hook("post_llm", ...)` 可工作（至少 1 个测试）
- [x] `agent.ask()` 无 `_ask_timing`、无根目录 `ask_timing` import
- [x] `AskTimingHook` 仅在 `hooks/ask_timing_hook.py`，经 `builtin.py` 注册
- [x] `hooks.yaml` + `HookConfig` 可关 `ask_timing`；关闭后不写 jsonl
- [x] OPT-ASK-TIMING 全部行为测试仍绿（纯对话 1 llm、交替、make_plan 方案 A、append、fail-open、stop、validation）
- [x] Phase 2 trace / shell_audit / custom hook 测试仍绿
- [x] 全量 pytest 仍绿；ruff 通过
- [x] 包根无 `ask_timing.py`

---

## 参考资料

- [`struct/phase2.md`](../struct/phase2.md) §5 — session/ask 级 Hook 方向
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) §10
- [`docs/command/OPT-ASK-TIMING.md`](./OPT-ASK-TIMING.md) — 计时口径
- [`docs/feedback/OPT-ASK-TIMING.md`](../feedback/OPT-ASK-TIMING.md)
- [`mini_coding_agent/hooks/registry.py`](../../mini_coding_agent/hooks/registry.py)
- [`mini_coding_agent/agent.py`](../../mini_coding_agent/agent.py)

---

*主 Agent 下达 · 一次做完 · 实现路径由子 Agent 自定*
