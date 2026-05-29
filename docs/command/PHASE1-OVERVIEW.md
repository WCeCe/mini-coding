# Phase 1 总规划（主 Agent）

> 本文档只定义 **目标、边界、规范**。  
> **不规定**具体类名、函数签名、实现顺序——由子 Agent 在约束内自主设计。

---

## 1. 阶段目标

在 `mini_coding_agent.py` 上交付 **变更治理层**，使文件修改可预览、可审批、可回滚、可审计，并达到 [`struct/06`](../struct/06-phase1-portfolio-and-depth.md) 的 Done Definition。

---

## 2. 范围边界

### 2.1 In Scope

- `write_file`、`patch_file` 的治理（diff、checkpoint、回滚、session 追溯）
- Git 脏树**只读**风险提示
- 满足可靠性契约的自动化测试
- README 用户说明

### 2.2 Out of Scope

- 修改模型 tool 协议 / `parse` 格式
- `run_shell` 治理或回滚
- Web UI、新 pip 依赖、拆多包
- 自动 `git commit`、一次 ask 全部撤销、Docker 沙箱

### 2.3 已对齐产品决策

见 [`struct/04-phase1-decisions-and-mvp.md`](../struct/04-phase1-decisions-and-mvp.md)。

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 依赖 | 标准库 + 现有 pytest，不新增运行时依赖 |
| 结构 | 主逻辑保持 `mini_coding_agent.py` 单文件 |
| 改动 | 最小 diff，不顺手重构无关代码 |
| 测试 | 新行为有 pytest；可用 `FakeModelClient`，不依赖 Ollama |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| Git | 不 `commit` / `push`（除非用户明确要求） |
| 模型协议 | 不改 `build_prefix` 中 tool 的 JSON/XML 约定 |

---

## 4. 任务一览

| TASK_ID | 目的 | 可以写代码 |
|---------|------|------------|
| [P1-CHANGE-GOVERNANCE](./P1-CHANGE-GOVERNANCE.md) | 实现变更治理 + 测试 | 是 |
| [P1-DOCS](./P1-DOCS.md) | README 等用户文档 | 否（仅文档） |
| [P1-REVIEW](./P1-REVIEW.md) | 对照 Done Definition 总验收 | 否 |

**建议顺序**：CHANGE-GOVERNANCE → DOCS → REVIEW。子 Agent 可在 CHANGE-GOVERNANCE 内自行分步，但只交一份 `feedback/P1-CHANGE-GOVERNANCE.md`。

---

## 5. 子 Agent 窗口开场白（用户复制）

```
你是本项目的子 Agent（执行者）。
请先读：
- @docs/command/PHASE1-OVERVIEW.md
- @docs/command/<TASK_ID>.md
- @docs/struct/05-phase1-implementation-design.md
- @docs/struct/06-phase1-portfolio-and-depth.md（§4 Done Definition）

在约束内自行设计方案并实现。
回报写入 docs/feedback/<TASK_ID>.md（含：你的方案摘要、如何满足契约与 Done Definition、验证结果）。
```

---

## 6. 主 Agent 验收方式

- 只对照 **Done Definition** 与 **可靠性契约**，不审查「是否按某步骤实现」
- 不通过：在 `feedback` 注明差距，交同一 TASK_ID 修订
- 通过：更新 `struct/README.md` 状态板

---

*command/PHASE1-OVERVIEW · 主 Agent 维护*
