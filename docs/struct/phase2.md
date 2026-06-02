# Phase 2：Hook 扩展 + 可观测 + 结构化重构

> **状态**：✅ 已完成（2026-06-01）  
> **验收**：`feedback/P2-REVIEW.md`、`feedback/P2.1-REVIEW.md` · 最终测试 **43 passed, 1 skipped**

本阶段分两步交付，同属 Phase 2：**先** Hook 扩展点与包重构，**再** 补齐用户可感知的三层 Hook 栈。

---

## 1. 已完成

### 1.1 Hook 扩展点 + 重构（原 P2）

在工具执行边界引入 observe-only Hook，并将单文件拆为 `mini_coding_agent/` 包；**Phase 1 治理语义不变**。

| 交付 | 说明 |
|------|------|
| Hook 机制 | `pre_tool` / `post_tool`，`HookRegistry` + `register_hook` |
| 内置 trace | `ToolTraceHook` → session `tool_trace`（步序、耗时、成败） |
| 契约 | 只观察；Hook 异常 **fail-open**；不跳过 approve / 治理 |
| 重构 | `agent.py`、`hooks/`、`session.py`、`workspace.py` 等 |
| CLI | 根 `mini_coding_agent.py` → `cli.main`，用法兼容 |

**调用链**：`run_tool` → `_invoke_tool_with_hooks` → validate → 治理/执行 → post。

### 1.2 用户可感知三层栈（原 P2.1）

在 Hook 架构上补齐终端可见性与配置，不推翻 observe-only 契约。

| 层 | 交付 |
|----|------|
| **第 1 层** | 每步 tool 终端一行摘要（步序、名、耗时、成败）→ `trace_display_hook` |
| **第 2 层** | Session trace（YAML 可关）+ Shell 审计告警（命中模式 → 终端 + session，**不阻断**） |
| **第 3 层** | `.mini-coding-agent/hooks.yaml` 启停内置 Hook；CLI 可覆盖 YAML |

**新增依赖**：`PyYAML`（仅读 Hook 配置，不加载外部脚本）。

---

## 2. 关键决策（摘要）

| # | 决策 | 选定 |
|---|------|------|
| 1 | 第一优先级 | Hook + 可观测；一套机制 + 伴随重构 |
| 2 | Hook 粒度 | 工具边界 `pre_tool` / `post_tool` |
| 3 | Hook 形态 | 进程内 Python 回调 |
| 4 | Hook 交互 | 只观察，不阻断、不改 args/result |
| 5 | 可见性 | 每步 tool 实时终端摘要（stderr） |
| 6 | 内置 Hook 配置 | 声明式 YAML 启停 |

---

## 3. 可靠性契约（摘要）

| 场景 | 要求 |
|------|------|
| Hook 异常 | fail-open，主流程继续 |
| 无 Hook | 等同 Phase 1 行为 |
| 治理 tool | pre/post 各一次；治理字段不被覆盖 |
| trace 展示关闭 | 终端无摘要；session trace 独立开关 |
| shell 审计命中 | 仅告警 + 记录，工具仍执行 |
| YAML 缺失/错误 | fail-open，用默认 |
| 回归 | Phase 1 全部 pytest 仍绿 |

**未保证**：Hook 阻断、改参、run_shell 回滚。

---

## 4. 评估（相对作品集目标）

**特点**

- 「执行层可插桩，协议层不动」— 扩展性 + 可观测一条线讲通
- 重构有 pytest 锁行为；三层栈 demo 直观（终端 / 内置 Hook / YAML）
- shell 审计补了 Phase 1 未治理 shell 的**观测面**（仍不阻断）

**不足**

- Shell 审计只告警不拦，面试官可能追问「为何不断」
- 依赖从纯 stdlib 变为 +PyYAML
- 仅 `pre_tool`/`post_tool`，无 session 级 Hook
- 危险模式列表有限；无 ask 结束汇总视图

---

## 5. 后续可优化（Phase 2 范围内）

| 优先级 | 方向 | 说明 |
|--------|------|------|
| P1 | Shell 审计 → 可选阻断 | 与 approve 分工：告警保留，denylist 命中可拒绝执行 |
| P1 | Hook `post_tool` success/failure 语义 | 独立 failure 钩子或明确约定 |
| P1 | 模式库可维护 | 文档化默认 pattern；YAML 可扩展 |
| P2 | session 级 Hook | `session_start` / `session_end` |
| P2 | trace 导出 / ask 结束汇总 | 总步数、总耗时、失败数 |
| P2 | `--quiet` 安静模式 | 关终端 trace + shell 告警，session trace 可选保留 |
| P2 | 自定义 Hook 示例与文档 | 降低扩展门槛 |
| P3 | YAML → JSON 选项 | 若希望减依赖，可评估 stdlib 配置 |
| P3 | 外部脚本 Hook | 需另定安全边界 |

---

## 6. 面试一句话

> Phase 2 在 run_tool 边界加了 pre/post Hook（只观察、fail-open），做了包重构；并加了终端实时 trace、shell 危险命令告警和 YAML 配置内置 Hook。审批仍走 approve，治理仍走 Phase 1 diff/checkpoint。

---

*Phase 2 唯一 struct 文档 · 执行细节见 `feedback/P2-*`、`feedback/P2.1-*`*
