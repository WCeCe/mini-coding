# 项目文档索引

本仓库文档按**职责**分为四个目录，避免单文件无限膨胀。主 Agent（战略对话窗口）维护 `struct` 与 `command`；用户维护 `my_research`；子 Agent 产出写入 `feedback`。

---

## 目录说明

| 目录 | 维护者 | 内容 | 何时更新 |
|------|--------|------|----------|
| [`struct/`](./struct/) | **主 Agent** | 构想、边界、契约、Done Definition、**用户可见文案中文规范**（[`04-user-facing-locale`](./struct/04-user-facing-locale.md)） | 战略/阶段变化时 |
| [`command/`](./command/) | **主 Agent** | **目标级**任务（不含实现步骤） | 派活时 |
| [`feedback/`](./feedback/) | **子 Agent → 主 Agent 审** | 任务完成后的回报文档 | 子 Agent 完成后新增文件 |
| [`my_research/`](./my_research/) | **用户** | 根据主 Agent 构思自行调研的笔记 | 用户调研过程中 |
| 根目录说明 | **主 Agent** | 阶段交付说明等 | 阶段交付时 |

---

## 协作工作流

```
主 Agent 更新 struct（构想 / 设计）
        │
        ├─► 用户按 struct 调研 → 写入 my_research/
        │
        ├─► 主 Agent 写 command/<TASK_ID>.md
        │
        ▼
用户在新对话 @command/xxx + @struct/ 相关文档
        │
        ▼
子 Agent 执行 → 写入 feedback/<TASK_ID>.md
        │
        ▼
用户将 feedback 带回主 Agent → 验收 / 更新 struct / 派发下一 command
```

---

## 子 Agent 窗口快速入口

1. 读 [`struct/README.md`](./struct/README.md) 了解项目背景
2. **当前主线**：读 [`struct/phase5-graph.md`](./struct/phase5-graph.md) + [`command/GOLDEN-LOOP-OVERVIEW.md`](./command/GOLDEN-LOOP-OVERVIEW.md)
3. 读被指派的 [`command/<TASK_ID>.md`](./command/)
4. 自行设计并实现；按 [`feedback/TEMPLATE.md`](./feedback/TEMPLATE.md) 写入 `feedback/<TASK_ID>.md`（含方案摘要与验收自证）

---

## 当前阶段（摘要）

- **Phase 1**：✅ 变更治理
- **Phase 2**：✅ Hook + 可观测 + 重构（含终端 trace、shell 审计、YAML）
- **阶段记录**（大阶段各一份）：[`phase1`](./struct/phase1.md) · [`phase2`](./struct/phase2.md) · [`phase3`](./struct/phase3.md) · [`phase4`](./struct/phase4.md)
- **Phase 3**：✅ 已结项 · 用户说明见根目录 [`README.md`](../README.md) § Task Planning
- **Phase 4**：✅ 已结项 · struct [`phase4`](./struct/phase4.md)
- **Phase 5**：✅ **结项** · struct [`phase5-graph`](./struct/phase5-graph.md)（含 DAG MVP + eval 黄金闭环 · live 2/5）· 用户说明见根目录 [`README.md`](../README.md) § Graph Harness (Phase 5)

---

## 代码与使用说明

- 运行与安装：[`../README.md`](../README.md)
- **Agent 重构**：✅ [`refactor-agent`](./struct/refactor-agent.md) · [`02-codebase-reference`](./struct/02-codebase-reference.md)
- 源代码：[`../mini_coding_agent/`](../mini_coding_agent/)（包）+ [`../mini_coding_agent.py`](../mini_coding_agent.py)（CLI 入口）

---

*文档体系 v5 · Phase 5 Graph ✅ 结项（P5 + GL · live 2/5）*
