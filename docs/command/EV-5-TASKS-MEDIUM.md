# EV-5-TASKS-MEDIUM — 任务集·一般档

## 元信息

- **TASK_ID**: EV-5-TASKS-MEDIUM
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P1
- **可以写代码**: 是
- **依赖**: EV-2-GRADING-SCHEMA

---

## 目标

新增 **≥3 条** `tier: medium` 的 `fix_bug` 任务，用于考 Locate / 推理（非仅 Generate）。至少满足以下各 1 条：

1. **消息不点名文件**（无 `File "foo.py"`），须从错误描述推断  
2. **两文件 import 链**（bug 在 A，表现于 B）  
3. **逻辑错但语法对**（必须 `grading: tests_only` + pytest）

---

## 约束

- 契约：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §3
- medium 任务 **默认** `grading: tests_only`
- **接受** live 0/N — feedback 须诚实记录，不阻塞任务验收
- `--fake` 须全绿（FakeModel 队列可设计为逐步 patch）
- 不新增 pip 依赖

---

## 交付物

- ≥3 条 medium 任务 + README 表
- pytest 覆盖 medium 的 fake 路径
- 回报：[`feedback/EV-5-TASKS-MEDIUM.md`](../feedback/EV-5-TASKS-MEDIUM.md) — 含可选 live 结果

---

## 验收标准

- [ ] medium ≥3 条，三类场景各 ≥1
- [ ] `--fake` 全绿
- [ ] 文档标明「medium live 预期低于 easy」
- [ ] pytest + ruff 通过

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)
