# feedback — 子 Agent 回报

本目录存放子 Agent **完成任务后**提交给主 Agent 审阅的文档。主 Agent 据此验收、更新 `struct/` 状态板、决定是否派发下一 `command/`。

---

## 命名规范

与任务单一致：

```
feedback/<TASK_ID>.md
```

---

## 主 Agent 验收流程

1. 对照 `command/<TASK_ID>.md` 的验收标准逐项勾选
2. 检查 scope：是否改了任务单外的文件
3. 实现类：确认 pytest / ruff 输出（或自行复跑）
4. 结论写入主 Agent 对话；必要时更新 `struct/README.md` 状态板
5. 不合格：在原 `feedback/` 文件末尾追加「主 Agent 复审」段，或重新派发修订任务

---

## 回报索引

| TASK_ID | 状态 | 主 Agent 结论 |
|---------|------|---------------|
| P1-CHANGE-GOVERNANCE | 通过 | 主 Agent 复审 2026-05-29 |
| P1-DOCS | 通过 | 主 Agent 复审 2026-05-29 |
| P1-REVIEW | 待审 | 子 Agent 结论：**通过** |

*验收后由主 Agent 更新。*

---

## 空白回报

复制 [`TEMPLATE.md`](./TEMPLATE.md) 为 `feedback/<TASK_ID>.md` 并填写。
