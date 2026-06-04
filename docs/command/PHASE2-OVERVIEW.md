# Phase 2 总规划（主 Agent · 第一次派活：Hook + 重构）

> 完整 Phase 2 见 [`struct/phase2.md`](../struct/phase2.md)（含后续三层栈与 YAML，见 `feedback/P2.1-*`）。

---

## 1. 阶段目标

在 Phase 1 变更治理之上，交付：

1. **一套**工具边界 Hook（`pre_tool` / `post_tool`，只观察）
2. **一个**内置参考 Hook（trace / 可观测性）
3. **有目的的结构化重构**，Phase 1 行为与测试不退化

达到 [`struct/phase2.md`](../struct/phase2.md) 的 Done Definition。

---

## 2. 范围边界

### 2.1 In Scope

- Hook 注册与 `pre_tool` / `post_tool` 调用
- 内置 trace（或等价）参考 Hook
- 模块/文件重构（Hook 驱动，非空搬家）
- Phase 1 全量 pytest 回归
- README Extension & Observability

### 2.2 Out of Scope

- Hook 阻断、修改 args/result
- 外部脚本 Hook、`hooks.json`
- `session_start` / `session_end` 等额外事件
- benchmark、Docker 沙箱、`run_shell` 回滚
- 新 pip 运行时依赖
- 修改模型 tool 协议 / `parse` 格式
- 变更 Phase 1 治理语义（diff、checkpoint、回滚规则）

### 2.3 已对齐产品决策

见 [`struct/phase2.md`](../struct/phase2.md)。

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 依赖 | 标准库 + 现有 pytest，不新增运行时依赖 |
| 结构 | 允许多模块；须在 `feedback` 说明模块 map 与入口 |
| 改动 | 重构 + Hook 最小必要 diff；不顺手改无关逻辑 |
| 注释 | **保留**：除非逻辑完全删除，否则保留既有注释。**新增**：生成/改动的代码须带适量注释（模块职责、非显而易见分支、可靠性契约），保证可读性 |
| 用户可见文案 | 中文；协议标识英文（铁律 §8 · [`struct/04-user-facing-locale.md`](../struct/04-user-facing-locale.md)） |
| 测试 | Phase 1 测试全绿；Hook 新行为有 pytest；`FakeModelClient`，不依赖 Ollama |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| Git | 不 `commit` / `push`（除非用户明确要求） |
| 模型协议 | 不改 `build_prefix` 中 tool 的 JSON/XML 约定 |
| Hook 契约 | 见 [`struct/phase2.md`](../struct/phase2.md) |

---

## 4. 任务一览

| TASK_ID | 目的 | 可以写代码 |
|---------|------|------------|
| [P2-HOOK-AND-REFACTOR](./P2-HOOK-AND-REFACTOR.md) | Hook + 重构 + 测试 | 是 |
| [P2-DOCS](./P2-DOCS.md) | README 等用户文档 | 否（仅文档） |
| [P2-REVIEW](./P2-REVIEW.md) | 对照 Done Definition 总验收 | 否 |

**建议顺序**：HOOK-AND-REFACTOR → DOCS → REVIEW。子 Agent 可在 HOOK-AND-REFACTOR 内自行分步，但只交一份 `feedback/P2-HOOK-AND-REFACTOR.md`。

---

## 5. 子 Agent 窗口开场白（用户复制）

```
你是本项目的子 Agent（执行者）。
请先读：
- @docs/command/PHASE2-OVERVIEW.md
- @docs/command/<TASK_ID>.md
- @docs/struct/phase2.md

在约束内自行设计方案并实现。
回报写入 docs/feedback/<TASK_ID>.md（含：方案摘要、模块 map、契约/Done Definition 自证、验证结果）。
```

---

## 6. 主 Agent 验收方式

- 只对照 **Done Definition** 与 **可靠性契约**，不审查「是否按某步骤实现」
- 不通过：在 `feedback` 注明差距，交同一 TASK_ID 修订
- 通过：更新 `struct/README.md` 状态板

---

*command/PHASE2-OVERVIEW · 主 Agent 维护*
