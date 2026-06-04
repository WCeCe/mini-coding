# Agent 重构总规划（主 Agent · 非 Phase）

> 完整边界见 [`struct/refactor-agent.md`](../struct/refactor-agent.md)。  
> **用户要求**：重构时**尽量不减少既有注释**；可新增；仅逻辑整段删除时才删对应注释。

---

## 1. 目标

将 `mini_coding_agent/agent.py` 从上帝类拆为 **编排器 + 子模块**（protocol / governance / prompt / tools），**行为与 Phase 1–4 契约不变**；清除 `write_file`/`patch_file` **dead path**。

---

## 2. 范围边界

### 2.1 In Scope

- R1–R4 四步模块迁移（见 struct §3）
- 注释随代码迁移；回报注释迁移说明
- 全量 pytest + ruff
- REFACTOR-REVIEW 后更新 `02-codebase-reference.md`

### 2.2 Out of Scope

- 新功能、benchmark、协议变更  
- ToolSpec 统一、session 形状变更  
- 新 pip 依赖  

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 行为 | **零行为变更**（除非 dead path 移除导致的不可达代码删除） |
| 注释 | **保留用户注释**；迁移时带走；见 struct/refactor-agent §5 |
| 测试 | 每步 `python -m pytest -q` 全绿；`FakeModelClient` |
| 验证 | `python -m ruff check .` |
| 改动 | 一步一 TASK；不顺手改无关模块 |
| Git | 不 commit/push（除非用户要求） |
| 铁律 | [`01-vision-and-roadmap.md`](../struct/01-vision-and-roadmap.md) §6–§8 |

---

## 4. 任务一览

| TASK_ID | 目的 | 可以写代码 | 依赖 | 状态 |
|---------|------|------------|------|------|
| [R1-PROTOCOL-EXTRACT](./R1-PROTOCOL-EXTRACT.md) | `protocol.py` | 是 | — | ✅ |
| [R2-GOVERNANCE-EXTRACT](./R2-GOVERNANCE-EXTRACT.md) | `governance.py` + dead path | 是 | R1 ✅ | ✅ |
| [R3-PROMPT-EXTRACT](./R3-PROMPT-EXTRACT.md) | `prompt.py` | 是 | R2 ✅ | ✅ |
| [R4-TOOLS-EXTRACT](./R4-TOOLS-EXTRACT.md) | `tools/` | 是 | R3 ✅ | ✅ |
| [REFACTOR-REVIEW](./REFACTOR-REVIEW.md) | 总验收 + 02 更新 | 否 | R4 ✅ | ✅ |

**顺序**：R1 → R2 → R3 → R4 → REVIEW（**不可跳步**）。

---

## 5. 子 Agent 开场白（用户复制）

```
你是本项目的子 Agent（执行者）。
请先读：
- @docs/command/REFACTOR-OVERVIEW.md
- @docs/command/<TASK_ID>.md
- @docs/struct/refactor-agent.md

严格执行任务单；注释尽量保留，迁移时带走。
回报写入 docs/feedback/<TASK_ID>.md（含注释迁移说明、pytest/ruff）。
```

---

## 6. 主 Agent 验收

- 对照 struct/refactor-agent Done Definition；不审查具体类名设计  
- 每步通过后再派下一步  

---

*command/REFACTOR-OVERVIEW · 主 Agent 维护*
