# Phase 2.1 总规划（历史派活记录）

> **已并入** [`struct/phase2.md`](../struct/phase2.md)。Phase 2.1 不是独立大阶段，仅为 Phase 2 的第二次派活。下文保留供 `feedback/P2.1-*` 对照。

---

## 1. 阶段目标

在 Phase 2 Hook 架构之上，交付 **三层 Hook 栈的用户可感知价值**：

1. **运行时可见** — 每步 tool 终端实时一行摘要  
2. **内置 Hook 有用** — trace 展示 + shell 审计/告警（只观察）  
3. **YAML 配置** — 启停内置 Hook（非外部脚本）

达到 [`struct/phase2.md`](../struct/phase2.md)（§1.2 三层栈部分）。

---

## 2. 范围边界

### 2.1 In Scope

- 终端 trace 展示（REPL + one-shot）
- Shell 审计/告警内置 Hook
- `.mini-coding-agent/hooks.yaml` + **PyYAML**
- Phase 1 / Phase 2 全量回归
- README 用户说明

### 2.2 Out of Scope

- Hook 阻断、修改 args/result
- 外部脚本、`hooks.json`、用户模块动态加载
- Benchmark、Docker 沙箱
- 修改模型 tool 协议
- 删除用户注释（除非对应逻辑已完全删除）

### 2.3 已对齐决策

见 [`struct/phase2.md`](../struct/phase2.md)。

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 依赖 | 标准库 + pytest + **PyYAML**（2.1 唯一新增运行时依赖） |
| 结构 | 在 `mini_coding_agent/` 包内扩展；不空重构 |
| 改动 | 最小 diff；不顺手改无关逻辑 |
| 注释 | **保留**：除非逻辑完全删除，否则保留既有用户注释。**新增**：生成/改动的代码须带适量注释，保证可读性 |
| 用户可见文案 | 中文；协议标识英文（铁律 §8 · [`struct/04-user-facing-locale.md`](../struct/04-user-facing-locale.md)） |
| 测试 | Phase 1/2 全绿；2.1 新行为有 pytest；`FakeModelClient` |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| Git | 不 `commit` / `push`（除非用户明确要求） |
| Hook 契约 | 见 [`struct/phase2.md`](../struct/phase2.md) |

---

## 4. 任务一览

| TASK_ID | 目的 | 可以写代码 |
|---------|------|------------|
| [P2.1-HOOK-USER-VALUE](./P2.1-HOOK-USER-VALUE.md) | 三层栈实现 + 测试 | 是 |
| [P2.1-DOCS](./P2.1-DOCS.md) | README | 否（仅文档） |
| [P2.1-REVIEW](./P2.1-REVIEW.md) | 总验收 | 否 |

**建议顺序**：HOOK-USER-VALUE → DOCS → REVIEW。

---

## 5. 子 Agent 窗口开场白（用户复制）

```
你是本项目的子 Agent（执行者）。
请先读：
- @docs/command/PHASE2.1-OVERVIEW.md
- @docs/command/P2.1-HOOK-USER-VALUE.md
- @docs/struct/phase2.md

在约束内自行设计方案并实现。
回报写入 docs/feedback/P2.1-HOOK-USER-VALUE.md
```

---

*command/PHASE2.1-OVERVIEW · 主 Agent 维护*
