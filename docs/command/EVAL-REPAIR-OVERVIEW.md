# Eval 修复与加固 — 派活总览（波次 C）

> **struct 契约**：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)  
> **前置**：Phase 5 + GL-1–5 ✅  
> **状态**：✅ **结项**（EV-REVIEW 2026-06-05）

---

## 1. 背景（一句话）

现有 eval 能证明 **管线可跑**，不能证明 **agent 够强**；本波次修复评分漏洞、加固 Generate、分档扩展任务集，并诚实区分 fake vs live 指标。

---

## 2. 当前优先级

| 优先级 | 说明 |
|--------|------|
| **P0** | EV-1 → EV-2 → EV-3（评分与 Generate；可 EV-2/3 并行但须等 EV-1 契约） |
| **P1** | EV-4 → EV-5 → EV-6 |
| **P2** | EV-7 → EV-REVIEW |
| **冻结** | SWE-bench、新 pip 依赖、非 fix_bug live 大盘、Gate 规则化 |

---

## 3. 任务单（严格顺序）

| 顺序 | TASK_ID | 任务单 | 可以写代码 | 依赖 | 状态 |
|------|---------|--------|------------|------|------|
| 1 | **EV-1** | [EV-1-VERIFY-ALIGN](./EV-1-VERIFY-ALIGN.md) | 是 | — | ✅ **通过** |
| 2 | **EV-2** | [EV-2-GRADING-SCHEMA](./EV-2-GRADING-SCHEMA.md) | 是 | EV-1 | ✅ **通过** |
| 3 | **EV-3** | [EV-3-GENERATE-ROBUST](./EV-3-GENERATE-ROBUST.md) | 是 | EV-1 | ✅ **通过** |
| 4 | **EV-4** | [EV-4-TASKS-EASY](./EV-4-TASKS-EASY.md) | 是 | EV-2 | ✅ **通过**（easy 12 条） |
| 5 | **EV-5** | [EV-5-TASKS-MEDIUM](./EV-5-TASKS-MEDIUM.md) | 是 | EV-2 | ✅ **通过**（medium 3 条） |
| 6 | **EV-6** | [EV-6-BASELINE-REPORT](./EV-6-BASELINE-REPORT.md) | 是 | EV-1–3 | ✅ **通过** |
| 7 | **EV-7** | [EV-7-DOCS-CI](./EV-7-DOCS-CI.md) | 是* | EV-4–6 | ✅ **通过** |
| 8 | **EV-REVIEW** | [EV-REVIEW](./EV-REVIEW.md) | 否 | EV-7 | ✅ **结项** |

\* EV-7 以文档与 CI 为主；代码改动限于 workflow 注释或可选 eval step。

**并行说明**：EV-3 与 EV-2 可并行（不同文件）；**EV-4 与 EV-5 可并行**（不同任务集）。**EV-REVIEW 须等 EV-1–7 全部 feedback 通过。**

---

## 4. 工程规范（全员）

| 规范 | 要求 |
|------|------|
| 范围 | eval + harness verify/generate/protocol；见各任务单 |
| 依赖 | **不新增** pip 包 |
| 改码 | patch/write 经 `run_tool` → governance |
| 测试 | 新逻辑 pytest；框架测 FakeModel |
| live | 手动跑并写入 `feedback/`；**不阻塞** EV 结项（除非任务单明确要求） |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| 回报 | `feedback/<TASK_ID>.md` |
| Git | 不 commit / push（除非用户明确要求） |
| 文案 | 铁律 §8 中文 |

---

## 5. 里程碑

| 标记 | 任务 | 标志 |
|------|------|------|
| M0 | EV-1 + EV-2 | 无双标准 verify；`grading` 字段可用 |
| M1 | EV-3 | live 失败模式有 pytest 覆盖 |
| M2 | EV-4 + EV-5 | easy ≥12、medium ≥3 |
| M3 | EV-6 | 基线对比 CLI |
| M4 | EV-REVIEW | struct Done Definition §7 全勾选 |

---

## 6. 子 Agent 开场白（复制即用）

### EV-1

```
你是子 Agent，任务 EV-1-VERIFY-ALIGN。
阅读 docs/struct/eval-repair-plan.md §5.1 与 docs/command/EV-1-VERIFY-ALIGN.md。
对齐 harness verify 与 eval 终判；修复 off_by_one_sum 类假阳性；含 lock_tests 或等价机制。
回报 docs/feedback/EV-1-VERIFY-ALIGN.md。
```

### EV-2

```
你是子 Agent，任务 EV-2-GRADING-SCHEMA。
阅读 docs/struct/eval-repair-plan.md §3、§5.2 与 docs/command/EV-2-GRADING-SCHEMA.md。
为 tasks.json 增加 tier/grading/lock_tests；更新 run_eval.py 与 eval/README.md。
依赖 EV-1 的 verify 行为。回报 docs/feedback/EV-2-GRADING-SCHEMA.md。
```

**主 Agent 派活令**：[`EVAL-REPAIR-DISPATCH.md`](./EVAL-REPAIR-DISPATCH.md)

---

*EVAL-REPAIR-OVERVIEW · 主 Agent · 2026-06-05*
