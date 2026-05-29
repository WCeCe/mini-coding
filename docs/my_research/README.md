# my_research — 用户调研笔记

本目录由**用户**维护，存放根据 [`struct/`](../struct/) 中主 Agent 构想**自行调研**的笔记与结论。

与子 Agent 的 [`feedback/`](../feedback/) 区分：

| | my_research | feedback |
|---|-------------|----------|
| 作者 | 用户 | 子 Agent |
| 目的 | 个人理解、对比、决策输入 | 任务交付与验收 |
| 审阅 | 主 Agent 与用户讨论 | 主 Agent 按 command 验收 |

---

## 目录约定

```
my_research/
├── README.md              # 本文件
├── phase_1/               # 第一阶段：变更治理
│   ├── research-plan.md   # 调研清单（主 Agent 给出）
│   ├── Aider.md
│   └── min_agent的变更代码逻辑.md
└── phase_2/               # 后续阶段（按需创建）
```

---

## 当前阶段

**Phase 1 — 变更治理**

- 调研清单：[`phase_1/research-plan.md`](./phase_1/research-plan.md)
- 构想与决策：[`struct/04-phase1-decisions-and-mvp.md`](../struct/04-phase1-decisions-and-mvp.md)
- 实现设计：[`struct/05-phase1-implementation-design.md`](../struct/05-phase1-implementation-design.md)

---

## 用户笔记索引

| 文件 | 主题 | 状态 |
|------|------|------|
| `phase_1/Aider.md` | Aider 变更与回滚机制 | 进行中 |
| `phase_1/min_agent的变更代码逻辑.md` | 本项目现有写文件链路 | 进行中 |

---

## 调研完成后

将结论摘要带回**主 Agent 对话**讨论；主 Agent 据此更新 `struct/` 或确认可进入 `command/` 实现阶段。

*用户无需按 feedback 模板写；自由笔记即可，但建议每篇文末有「结论 / 待讨论」小节。*
