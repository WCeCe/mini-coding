# 子 Agent 回报：OPT-WAIT-DISPLAY

## 元信息

- **TASK_ID**: OPT-WAIT-DISPLAY
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

### 挂接点

新增 `mini_coding_agent/wait_display.py`，提供 `WaitDisplay` 上下文管理器与 `complete_with_wait_display()` 包装函数。所有生产路径上的阻塞式 `model_client.complete()` 均经此包装：

| 调用点 | 模块 | 等待文案 |
|--------|------|----------|
| `ask()` 主循环 | `agent.py` | `正在等待模型响应…` |
| `tool_make_plan` | `tools/implementations.py` | `正在生成任务规划…` |
| `tool_delegate` → `child.ask()` | 间接经 `agent.py` | `正在等待模型响应…` |

未改 `OllamaModelClient.complete` 内部实现；包装层在调用前后控制 stderr 输出。

### TTY 判定与 spinner 行为

```
complete_with_wait_display(...)
  └─ with WaitDisplay(message):
       ├─ _enabled=False → 无输出（测试用 set_wait_display_enabled(False)）
       ├─ stderr.isatty()=True  → 后台线程 \r + Braille spinner 动画（100ms/帧）
       │                         退出时 _clear_line()：\r + 空格覆写 + \r
       └─ stderr.isatty()=False → 单行 print(message) 到 stderr，无 \r 动画
```

- **stderr 单行**：TTY 下始终 `\r` 回到行首更新同一行；与 stdout 的 `<final>` 回答、`[mini-agent]` trace 行分离。
- **输出顺序**（典型 tool 路径）：`等待指示` →（模型返回，TTY 清除 spinner 行）→ `trace 行` → 下一轮 `等待指示` → … → stdout final。
- **默认始终开启**；无 CLI 关闭旗标。测试通过 `set_wait_display_enabled(False)` 隔离。

### 与 trace_display 的关系

| 类型 | 通道 | 触发时机 |
|------|------|----------|
| 等待指示 | stderr | 每次 `complete()` 阻塞期间 |
| trace 展示 | stderr | 每次 tool 完成后（既有 Hook） |

二者均写 stderr，但等待指示在推理结束即清除（TTY），不会与后续 trace 行混在同一物理行。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据（测试名 / 行为说明） |
|------|----------|---------------------------|
| REPL / one-shot：模型返回前 stderr 可见等待指示 | ✅ | `test_wait_display_non_tty_prints_static_message`；TTY 动画见 `test_wait_display_tty_clears_spinner_line` |
| 模型返回后 spinner 清除，stdout final / trace 不被污染 | ✅ | `test_wait_display_tty_clears_spinner_line`（末尾 `\r` 覆写）；`test_wait_display_before_trace_display_order` |
| `make_plan` 内 `complete()` 同样有指示 | ✅ | `test_wait_display_during_make_plan` |
| 非 TTY：无破坏性 `\r` 刷屏 | ✅ | `test_wait_display_non_tty_prints_static_message` 断言 `"\r" not in captured.err` |
| 新增 pytest；全量仍绿 | ✅ | 5 个 wait_display 测试；全量 71 passed, 1 skipped |
| 无新 pip 依赖 | ✅ | 仅用 `sys` / `threading` 标准库 |
| 中文等待文案 | ✅ | `MESSAGE_MODEL` / `MESSAGE_PLAN` |
| FakeModelClient 不 flaky | ✅ | `set_wait_display_enabled(False)` + `restore_wait_display` fixture；instant complete 下现有 66+ 测试无回归 |
| 不改 stream 协议 / tool 协议 / Phase 1–4 语义 | ✅ | 仅包装 `complete()` 调用；diff 限于 wait_display + 两处 import |

---

## 交付物

| 路径 | 说明 |
|------|------|
| `mini_coding_agent/wait_display.py` | 新增：WaitDisplay、complete_with_wait_display、set_wait_display_enabled |
| `mini_coding_agent/agent.py` | ask() 内 complete 改经 wait 包装 |
| `mini_coding_agent/tools/implementations.py` | tool_make_plan 内 complete 改经 wait 包装 |
| `tests/test_mini_coding_agent.py` | +5 测试 + restore_wait_display fixture |
| `docs/feedback/OPT-WAIT-DISPLAY.md` | 本回报 |

---

## 验证结果

```
$ python -m pytest tests/test_mini_coding_agent.py -q
...........s............................................................
71 passed, 1 skipped in 44.35s

$ python -m ruff check mini_coding_agent/wait_display.py mini_coding_agent/agent.py mini_coding_agent/tools/implementations.py tests/test_mini_coding_agent.py
All checks passed!
```

---

## 风险与未解决问题

- **capsys 与 TTY spinner**：pytest `capsys` 会累积 spinner 中间帧历史；TTY 测试仅断言末尾 `\r` 覆写，不代表真实终端「视觉上完全空白」。真实 REPL 下 `_clear_line()` 行为已按 trace_display 同类单行模式实现。
- **并发 complete**：当前架构为单线程阻塞调用，无并行 complete；若未来并行化需评估 spinner 行互斥。
- **Windows 旧终端**：清除行使用 `\r` + 空格，未依赖 ANSI `\033[K`；与现代 Windows Terminal 兼容，极旧 cmd 可能留少量空格残留（与任务约束下可接受）。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: 通过
- **备注**: 主 Agent 独立复跑 `pytest`（71 passed, 1 skipped）与 `ruff`（All checks passed）；挂接点、TTY/非 TTY 行为、与 trace 顺序均符合 `OPT-WAIT-DISPLAY` 契约。风险节（capsys 中间帧、单线程假设）已记录，不阻塞结项。
