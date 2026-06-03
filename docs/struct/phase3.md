# Phase 3：任务规划与 Coding 链路深度

> **状态**：✅ Phase 3 已结项（2026-06-02）· 交付 `make_plan` + `--plan-first` + 文档  
> **策略**：先设计 coding 链路深度，**暂缓** benchmark 量化。Skill 加载见 [**Phase 4**](./phase4.md)。

---

## 1. 阶段目标

在 Phase 1 变更治理 + Phase 2 Hook 可观测之上，补齐 **「复杂任务 → 可执行计划 → 逐步 coding」** 的设计深度，使 Agent 能拆分任务、记住计划、仍走既有治理与 Hook 链路。

**本阶段叙事（面试可讲）**：

```
复杂需求 →（可选）read/search 调查 → make_plan → 对照 plan 逐步 tool → Phase1 diff/checkpoint → Phase2 trace
```

---

## 1.1 Phase 3 首项 ✅（2026-06-02）

| 任务 | 状态 |
|------|------|
| P3-MAKE-PLAN | ✅ |
| P3-DOCS | ✅ |
| P3-REVIEW | ✅ |

| 交付 | 说明 |
|------|------|
| `make_plan` | `planning.py` + `agent.py`；单次 complete；`memory.plan` |
| `--plan-first` | 本轮 ask 内须先成功 plan 再 risky tool |
| 文档 | [`README.md`](../README.md) § Task Planning |
| 测试 | 53 passed, 1 skipped |
| 验收 | [`feedback/P3-REVIEW.md`](../feedback/P3-REVIEW.md) |

**文案规范**：全包用户可见字符串已按 [`04-user-facing-locale.md`](./04-user-facing-locale.md)（铁律 §7）中文化；规划成功前缀 `规划成功`；JSON **字段名英文、值建议中文**。行为与 P3-REVIEW 一致。

---

## 2. 范围边界

### 2.1 In Scope（按优先级）

| 优先级 | 方向 | TASK_ID | 说明 |
|--------|------|---------|------|
| **P0** | 任务规划工具 | P3-MAKE-PLAN | ✅ 已完成 |
| **暂缓** | 规划与执行衔接 | — | 非 Phase 3 交付范围；需时另立项 |
| **暂缓** | `run_shell` 可选阻断 | — | 见 [`phase2.md`](./phase2.md) §5；非 Phase 3 交付范围 |
| **暂缓** | benchmark / 回归任务集 | — | 等 coding 链路设计稳后再量化 |

### 2.2 Out of Scope

- benchmark、SWE-bench、Docker 沙箱
- 自动逐步执行 plan（隐式编排器）
- plan 默认落盘文件（MVP 仅 session memory）
- 新 pip 运行时依赖（延续 stdlib + 已有 PyYAML）
- 修改 Phase 1 治理语义；Hook 阻断/改参（plan 工具本身 observe-only 链路不变）
- 多模型 / 流式（按需，非 Phase 3 近期）

### 2.3 已对齐产品决策

| # | 决策 | 选定 |
|---|------|------|
| 1 | Phase 3 重心 | 先 coding 设计深度，后量化 |
| 2 | 首项交付 | `make_plan` 工具 |
| 3 | 计划粒度 | **任务级**（含 acceptance；不写函数级清单） |
| 4 | 触发方式 | 默认模型自主（prompt 引导）；CLI `--plan-first` 强制先规划 |
| 5 | 与 `delegate` 关系 | **并列**：delegate=只读调查子 Agent；make_plan=单次结构化拆分 |
| 6 | benchmark | **暂缓**，不进 Phase 3 近期交付 |

---
## 3. P3-MAKE-PLAN Done Definition

首项验收以 [`command/P3-MAKE-PLAN.md`](../command/P3-MAKE-PLAN.md) 为准；摘要如下：

| # | 交付 | 要求 |
|---|------|------|
| 1 | 工具 `make_plan` | `risky: False`；参数至少 `goal`（必填）、`context`（可选） |
| 2 | 规划调用 | 工具内 **单次** `model_client.complete()` + 专用 planning prompt；**无**内部 tool 循环 |
| 3 | 结构化输出 | 可解析 JSON：`goal`、`steps[]`（含 id/title/acceptance，可选 risky 提示）、`assumptions`、`out_of_scope`；步数上限合理（建议 ≤12） |
| 4 | Session 持久化 | 写入 `session["memory"]["plan"]`；`memory_text()` 展示当前 plan 摘要 |
| 5 | Prompt 引导 | `build_prefix` 规则：多文件/含糊/用户要规划时，先调查再 `make_plan` 再执行 |
| 6 | CLI `--plan-first` | 开启时：该次 `ask` 在首次 risky tool 之前须已成功 `make_plan`（具体 enforcement 由子 Agent 设计并在 feedback 说明） |
| 7 | Hook / 治理 | 走现有 `run_tool` 链路；Phase 1 治理与 Phase 2 Hook 契约不变 |
| 8 | 测试 | pytest + `FakeModelClient`；覆盖解析、校验、memory、CLI 开关；Phase 1/2 回归仍绿 |
| 9 | 文档 | README 简述工具与 `--plan-first`；回报见 `feedback/P3-MAKE-PLAN.md` |

**明确不做（首项）**：自动按 plan 逐步 dispatch；`mark_step_done` 状态机；写 `.mini-coding-agent/plan.md`。

---

## 4. 可靠性契约（摘要 · P3-MAKE-PLAN）

| 场景 | 要求 |
|------|------|
| 模型返回非法 JSON | 工具返回明确错误；主循环可 retry；不写 memory.plan |
| `goal` 为空 | validate 拒绝 |
| `--plan-first` 未 plan 即调 risky tool | 拒绝并提示先 `make_plan` |
| `--plan-first` 关闭 | 与 Phase 2 行为一致；plan 可选 |
| plan 成功 | memory.plan 更新；后续轮次 prompt 可见 |
| Hook 异常 | 仍 fail-open |
| 子 Agent depth | `make_plan` 在 read_only 子 Agent 中可用与否：须与 delegate 深度策略一致并在 feedback 说明 |

---

## 5. 评估（相对作品集目标）

**预期特点**

- 与 `delegate` 分工清晰：「调查 vs 规划 vs 执行」
- 仍走 Phase 1 治理，plan 不绕过 diff/checkpoint
- `--plan-first` 可 demo「复杂任务先想清楚再动手」

**已知取舍**

- 首版无步骤完成度追踪，靠 memory + 模型自觉
- plan 质量依赖模型与 planning prompt，暂无 benchmark 打分
- `--plan-first` 已落地；每轮 `ask()` 重置 satisfied

---

## 6. 可选后续（未纳入 Phase 3 结项）

| 方向 | 说明 |
|------|------|
| 规划与执行衔接 | 例如在 notes/final 中对照 step id；或轻量「当前 step」memory 字段 |
| Shell 审计 → 可选阻断 | 见 [`phase2.md`](./phase2.md) §5 |
| benchmark | 自建小任务集 + 自动评分 |

**Skill 加载**已划入 [**Phase 4**](./phase4.md)（P4-SKILLS）。

Phase 1/2 范围内优化仍见各 `phase*.md` §5，不拆独立大阶段。

---

## 7. 面试一句话

> Phase 3 加了 `make_plan`：复杂任务先拆成带验收标准的步骤并放进 session；默认 Agent 自主决定何时规划，也可用 `--plan-first` 强制；执行仍走 Phase 1 diff/checkpoint 和 Phase 2 trace，benchmark 等量化的留到链路设计稳之后。

---

## 8. 代码与文档索引（首项）

| 类型 | 路径 |
|------|------|
| 规划模块 | `mini_coding_agent/planning.py` |
| 工具/门控/memory | `mini_coding_agent/agent.py`（Task Planning、`memory_text`、门控） |
| CLI | `mini_coding_agent/cli.py`（`--plan-first`） |
| 测试 | `tests/test_mini_coding_agent.py`（Phase 3 段） |
| 用户说明 | [`README.md`](../README.md) § Task Planning |
| 派活/验收 | [`command/`](../command/) · [`feedback/`](../feedback/) |

---

## 9. 任务与回报一览

| TASK_ID | 类型 | 回报 |
|---------|------|------|
| P3-MAKE-PLAN | 实现 | [`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md) |
| P3-DOCS | 文档 | [`feedback/P3-DOCS.md`](../feedback/P3-DOCS.md) |
| P3-REVIEW | 验收 | [`feedback/P3-REVIEW.md`](../feedback/P3-REVIEW.md) |

---

*Phase 3 struct 文档 · 下一阶段 [`phase4.md`](./phase4.md)*
