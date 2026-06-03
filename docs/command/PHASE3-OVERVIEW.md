# Phase 3 总规划（主 Agent · Coding 链路深度）

> 完整 Phase 3 见 [`struct/phase3.md`](../struct/phase3.md)。  
> **策略**：先设计 planning + coding 深度；**benchmark 量化暂缓**。

---

## 1. 阶段目标

在 Phase 1/2 之上，交付 **「复杂任务 → 计划 → 逐步 coding」** 能力，达到 [`struct/phase3.md`](../struct/phase3.md) 的 Done Definition（按子项递进）。

**首项**：`make_plan` 工具 + `--plan-first` CLI。

---

## 2. 范围边界

### 2.1 In Scope（近期）

- 只读规划工具 `make_plan`（单次模型调用、结构化 JSON、session memory）
- CLI `--plan-first`（强制先规划再 risky tool）
- Prompt 规则引导（何时先 plan）
- pytest 覆盖；Phase 1/2 全量回归

### 2.2 Out of Scope

- benchmark、SWE-bench、Docker 沙箱
- plan 自动编排 / 逐步 auto-dispatch
- plan 默认写盘
- Hook 阻断或改参（plan 工具除外：`--plan-first` 对 risky tool 的 gate 属产品行为，须在 feedback 说明且不绕过 approve/治理）
- 新 pip 运行时依赖
- 变更 Phase 1 治理语义
- 多模型 / 流式

### 2.3 已对齐产品决策

见 [`struct/phase3.md`](../struct/phase3.md) §2.3。

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 依赖 | 标准库 + 已有 PyYAML + pytest；不新增运行时依赖 |
| 结构 | 改动跟着功能走；不顺手空重构 |
| 改动 | 最小必要 diff |
| 注释 | **保留**既有用户注释；**新增**代码带适量注释（铁律 §5–§6） |
| 用户可见文案 | **中文**；工具名/参数名/JSON 字段/协议标签保持英文（铁律 §7 · [`struct/04-user-facing-locale.md`](../struct/04-user-facing-locale.md)） |
| 测试 | 新行为有 pytest；`FakeModelClient`；不依赖 Ollama |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| Git | 不 `commit` / `push`（除非用户明确要求） |
| 模型协议 | 现有 tool JSON/XML 格式保持；可新增 `make_plan` 工具条目与示例 |
| Hook 契约 | Phase 2 observe-only、fail-open 不变 |
| 治理 | Phase 1 diff/checkpoint/回滚语义不变 |

---

## 4. 任务一览

| TASK_ID | 目的 | 可以写代码 | 状态 |
|---------|------|------------|------|
| [P3-MAKE-PLAN](./P3-MAKE-PLAN.md) | `make_plan` + memory + `--plan-first` + 测试 | 是 | ✅ |
| [P3-DOCS](./P3-DOCS.md) | README 用户说明 | 否 | ✅ |
| [P3-REVIEW](./P3-REVIEW.md) | Phase 3 首项总验收 | 否 | ✅ |

**Phase 3 已结项**。下一阶段 Skill 见 [PHASE4-OVERVIEW](./PHASE4-OVERVIEW.md) · [P4-SKILLS](./P4-SKILLS.md)。  
**用户文档**：[`README.md`](../../README.md) § Task Planning (Phase 3)

---

## 5. 子 Agent 窗口开场白（用户复制）

```
你是本项目的子 Agent（执行者）。
请先读：
- @docs/command/PHASE3-OVERVIEW.md
- @docs/command/P3-MAKE-PLAN.md
- @docs/struct/phase3.md

在约束内自行设计方案并实现。
回报写入 docs/feedback/P3-MAKE-PLAN.md（含：方案摘要、契约/Done Definition 自证、pytest/ruff 输出）。
```

---

## 6. 主 Agent 验收方式

- 只对照 **Done Definition** 与 **可靠性契约**，不审查具体实现步骤
- 不通过：在 `feedback` 注明差距，交同一 TASK_ID 修订
- 通过：更新 `struct/README.md` 状态板；首项通过后派 P3-DOCS / P3-REVIEW

---

*command/PHASE3-OVERVIEW · 主 Agent 维护*
