# 项目文档索引

本仓库文档按**职责**分为四个目录，避免单文件无限膨胀。主 Agent（战略对话窗口）维护 `struct` 与 `command`；用户维护 `my_research`；子 Agent 产出写入 `feedback`。

---

## 目录说明

| 目录 | 维护者 | 内容 | 何时更新 |
|------|--------|------|----------|
| [`struct/`](./struct/) | **主 Agent** | 构想、边界、契约、Done Definition | 战略/阶段变化时 |
| [`command/`](./command/) | **主 Agent** | **目标级**任务（不含实现步骤） | 派活时 |
| [`feedback/`](./feedback/) | **子 Agent → 主 Agent 审** | 任务完成后的回报文档 | 子 Agent 完成后新增文件 |
| [`my_research/`](./my_research/) | **用户** | 根据主 Agent 构思自行调研的笔记 | 用户调研过程中 |

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
2. 读被指派的 [`command/<TASK_ID>.md`](./command/)
3. 自行设计并实现；按 [`feedback/TEMPLATE.md`](./feedback/TEMPLATE.md) 写入 `feedback/<TASK_ID>.md`（含方案摘要与验收自证）

---

## 当前阶段（摘要）

- **战略**：第一阶段 **变更治理层**（diff、checkpoint、回滚）
- **作品集定位**：见 [`struct/06-phase1-portfolio-and-depth.md`](./struct/06-phase1-portfolio-and-depth.md)
- **四个决策**：已对齐（见 [`struct/04`](./struct/04-phase1-decisions-and-mvp.md)）
- **执行**：子 Agent 按 [`command/P1-CHANGE-GOVERNANCE.md`](./command/P1-CHANGE-GOVERNANCE.md) 在约束内自行设计实现

---

## 代码与使用说明

- 运行与安装：[`../README.md`](../README.md)
- 源代码：[`../mini_coding_agent.py`](../mini_coding_agent.py)

---

*文档体系 v2 · 2026-05-29*
