# 任务单：P3-WALKTHROUGH

## 元信息

- **TASK_ID**: P3-WALKTHROUGH
- **TASK_TYPE**: DOCS + 注释优化（无行为变更）
- **优先级**: P1
- **可以写代码**: 是（**仅**增补/改写注释，禁止改逻辑）
- **依赖**: P3-REVIEW ✅

---

## 目标

1. 用**中文**写一份 Phase 3 **首项**说明，面向「想搞懂项目改了什么」的读者：做了哪些能力、和 Phase 1/2 如何衔接、典型使用场景（含 `--plan-first`）。
2. 梳理 **代码变动清单**（文件级 + 关键符号/流程），附简图或步骤说明。
3. 在 Phase 3 相关代码中**把注释写得更清楚**（模块职责、数据流、`--plan-first` 门控时机、与 `delegate` 区别），**不改变任何运行时行为**。

---

## 约束

- 见 [`PHASE3-OVERVIEW.md`](./PHASE3-OVERVIEW.md) §3 工程规范
- **铁律**：保留所有既有用户注释；可改写措辞使其更清晰，**不得**因「整理」而删除
- **禁止**：改工具行为、改 JSON schema、改测试断言、新依赖、benchmark、自动编排
- 说明范围仅限 **Phase 3 首项**（`make_plan` + `memory.plan` + `--plan-first` + README 已有内容）；不展开 §6 未派活项
- 文风：通俗、有结构；避免堆砌类名；关键处可配 mermaid 或 ASCII 流程图
- 对照实现写，以 [`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md) 为事实来源，发现与 README 矛盾须在回报中注明

---

## 交付物

| 交付 | 路径 |
|------|------|
| 中文说明（主交付） | [`docs/PHASE3-WALKTHROUGH-zh.md`](../PHASE3-WALKTHROUGH-zh.md)（新建，用户可读） |
| 注释优化 | `mini_coding_agent/planning.py`、`mini_coding_agent/agent.py`（Phase 3 相关段落）、`mini_coding_agent/cli.py`（`--plan-first`） |
| 回报 | [`feedback/P3-WALKTHROUGH.md`](../feedback/P3-WALKTHROUGH.md)（改了哪些文件、注释原则、pytest/ruff） |

### `PHASE3-WALKTHROUGH-zh.md` 建议目录（可微调）

1. Phase 3 首项一句话总结  
2. 解决了什么问题（相对 Phase 2）  
3. 用户能做什么（`make_plan`、默认自主规划、`--plan-first`、`/memory`）  
4. `delegate` vs `make_plan` 对比表  
5. 一次请求的代码路径（从 `ask()` 到 `tool_make_plan` / 门控）  
6. 代码变动清单（文件 → 职责 → 关键函数）  
7. Session 里 `memory.plan` 长什么样  
8. 已知限制（与 README limitations 一致）  
9. 和后续 Phase 3 项的关系（一句话，不展开实现）

---

## 验收标准

- [ ] `docs/PHASE3-WALKTHROUGH-zh.md` 存在且为中文，非技术人员能读懂大意
- [ ] 含代码变动清单与至少一条端到端流程说明
- [ ] Phase 3 相关源文件注释更清晰（模块头、门控分支、`_ask_plan_satisfied` 生命周期）
- [ ] **无行为变更**：`python -m pytest -q` 全绿（53 passed, 1 skipped）；`ruff check .` 通过
- [ ] `feedback/P3-WALKTHROUGH.md` 落盘，含 pytest/ruff 输出摘要

---

## 参考资料

- [`struct/phase3.md`](../struct/phase3.md)
- [`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md)
- [`feedback/P3-DOCS.md`](../feedback/P3-DOCS.md)
- [`feedback/P3-REVIEW.md`](../feedback/P3-REVIEW.md)
- [`README.md`](../../README.md) § Task Planning (Phase 3)

---

*实现路径由子 Agent 自定*
