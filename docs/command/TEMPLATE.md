# 子 Agent 任务单模板

> 复制为 `command/<TASK_ID>.md`。主 Agent 只填**目标、约束、验收**；不填实现步骤。

---

## 元信息

- **TASK_ID**:
- **TASK_TYPE**: RESEARCH | IMPLEMENT | DOCS | REVIEW
- **优先级**: P0 | P1 | P2
- **可以写代码**: 是 / 否
- **依赖**（可选）:

---

## 目标

（要达成什么结果，1–3 句）



---

## 约束

（边界、规范、禁止项；可引用 `struct/`、各 Phase OVERVIEW §3；含 [`struct/01`](../struct/01-vision-and-roadmap.md) 铁律 §5 **保留用户注释**、§6 **新增代码须有注释**、§7 **用户可见文案中文**（[`04-user-facing-locale`](../struct/04-user-facing-locale.md)））



---

## 交付物

- 代码/文档路径：
- 回报：[`feedback/<TASK_ID>.md`](../feedback/)（须含**方案摘要**、**验收自证**、**完整 pytest/ruff 输出**；子 Agent 一次完成实现与验证，主 Agent 仅复审最终结果）

---

## 验收标准

（可勾选项；对照 `struct/06` Done Definition 或具体指标）

- [ ] 

---

## 参考资料

- 

---

*实现路径由子 Agent 自定*
