# 任务单：OPT-WAIT-DISPLAY

## 元信息

- **TASK_ID**: OPT-WAIT-DISPLAY
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P1
- **可以写代码**: 是
- **性质**: 横切 UX 优化（非新 Phase）

---

## 背景

用户 REPL 输入「你好」等纯对话时，在第一次 `model_client.complete()` 返回前终端完全静默（可能数分钟）。Phase 2 `trace_display` 仅在 **tool 完成后** 输出，无法覆盖「仅等模型、无 tool」的空窗期。

---

## 目标

在每次阻塞式模型推理（`complete()`）期间，向 **stderr** 显示 **单行 spinner**，让用户感知程序仍在运行；推理结束后清除该行，不与 stdout 的 `<final>` 回答或既有 trace 行混排。

须覆盖所有生产路径上的 `complete()` 调用（含 `ask()` 主循环、`make_plan`、经 `delegate` 触发的子 Agent 等）。

---

## 约束

- 见 [`struct/01-vision-and-roadmap.md`](../struct/01-vision-and-roadmap.md) 铁律：标准库优先、新行为必有 pytest（`FakeModelClient`）、保留用户注释、新增代码适量注释
- 见 [`struct/04-user-facing-locale.md`](../struct/04-user-facing-locale.md)：等待提示文案 **中文**；协议/代码标识保持英文
- **stderr 单行 spinner**（已与用户对齐）；**不提供** `--no-wait-display` 等关闭旗标 — **默认始终开启**
- **非 TTY**（输出重定向、CI）：不做 `\r` 动画刷屏；至少一行静态提示即可
- **不**改 Ollama `stream` 协议、不引入新 pip 依赖、不改 tool 协议与 Phase 1–4 产品语义
- 测试路径使用 `FakeModelClient` 时不应因 spinner 线程导致 flaky；子 Agent 自行设计 enable/disable 或包装策略

---

## 交付物

1. 代码：`mini_coding_agent/`（及必要时的 `tests/`）
2. 回报：[`feedback/OPT-WAIT-DISPLAY.md`](../feedback/OPT-WAIT-DISPLAY.md)，须含：
   - **方案摘要**（spinner 挂接点、TTY 判定、与 trace 行的输出顺序）
   - **契约对照表**
   - **Done Definition 自证**
   - pytest / ruff 输出

---

## 验收标准

- [x] REPL / one-shot：用户发消息后，在模型返回前 stderr 可见单行等待指示（TTY 下有动画）
- [x] 模型返回后：spinner 行被清除或结束，stdout final 与 `[mini-agent]` trace 行不被 spinner 残留污染
- [x] `make_plan` 内 `complete()` 等待期间同样有指示（不仅主循环第一次）
- [x] 非 TTY：无破坏性 `\r` 刷屏；行为可测
- [x] 新增 pytest 覆盖等待指示的核心行为；全量 pytest 仍绿
- [x] 无新 pip 依赖

---

## 参考资料

- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) — `ask()` 主循环、`OllamaModelClient.complete`
- [`mini_coding_agent/models.py`](../../mini_coding_agent/models.py)
- [`mini_coding_agent/agent.py`](../../mini_coding_agent/agent.py) — `ask()` 内 `complete()`
- [`mini_coding_agent/tools/implementations.py`](../../mini_coding_agent/tools/implementations.py) — `tool_make_plan` 内 `complete()`
- [`mini_coding_agent/hooks/trace_display_hook.py`](../../mini_coding_agent/hooks/trace_display_hook.py) — 既有 stderr 单行模式参考

---

*主 Agent 下达 · 实现路径由子 Agent 自定*
