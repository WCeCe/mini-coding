# 主 Agent 派活令 — Eval 波次 C

> **发布者**：主 Agent  
> **发布日期**：2026-06-05  
> **契约**：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)  
> **任务索引**：[`EVAL-REPAIR-OVERVIEW.md`](./EVAL-REPAIR-OVERVIEW.md)

---

## 0. 战略对齐（全员必读）

黄金闭环 GL 已结项（live **2/5**）。主 Agent 审计结论：**eval 管线可跑，但不能证明 agent 够强**。波次 C 优先修复 **verify 双标准**、**grading schema**、**Generate 鲁棒性**，再扩展任务分档。

**铁律**：不新增 pip 依赖；`--fake` 全绿 ≠ agent 能力；接受 live 短期 &lt;5/5。

---

## 1. 派活波次（禁止跳波）

| 波次 | 任务 | 条件 | 窗口数 |
|------|------|------|--------|
| **Wave 1** | EV-1-VERIFY-ALIGN | 立即派 | **1** |
| **Wave 2** | EV-2 + EV-3 | Wave 1 feedback **主 Agent 验收通过** | 最多 **2**（可并行） |
| **Wave 3** | EV-4 + EV-5 | Wave 2 **全部**验收通过 | 最多 **2**（可并行） |
| **Wave 4** | EV-6-BASELINE-REPORT | Wave 3 验收通过 | **1** |
| **Wave 5** | EV-7-DOCS-CI | Wave 4 验收通过 | **1** |
| **Wave 6** | EV-REVIEW | Wave 5 feedback 提交 | 主 Agent 自审 |

**当前状态（主 Agent 维护）**：

| TASK_ID | 波次 | 派活状态 | 验收状态 |
|---------|------|----------|----------|
| EV-1-VERIFY-ALIGN | 1 | ✅ 已派 | ✅ **通过**（2026-06-05 · fake 5/5 · pytest 177） |
| EV-2-GRADING-SCHEMA | 2 | ✅ 已派 | ✅ **通过**（2026-06-05 · fake 5/5 · pytest 186） |
| EV-3-GENERATE-ROBUST | 2 | ✅ 已派 | ✅ **通过**（2026-06-05 · live 原 fail 仍 fail，单测 OK） |
| EV-4-TASKS-EASY | 3 | ✅ 已派 | ✅ **通过**（easy 12 条 · fake 15/15） |
| EV-5-TASKS-MEDIUM | 3 | ✅ 已派 | ✅ **通过**（medium 3 条） |
| EV-6-BASELINE-REPORT | 4 | ✅ 已派 | ✅ **通过** |
| EV-7-DOCS-CI | 5 | ✅ 已派 | ✅ **通过** |
| EV-REVIEW | 6 | ✅ 结项 | ✅ **波次 C 结项** |

---

## 2. Wave 1 — 立即执行

### 任务：EV-1-VERIFY-ALIGN

**目标**：对齐 harness `verify` 与 eval 终判；消除 `off_by_one_sum` 类假阳性；含 `lock_tests` 基础行为。

**任务单**：[`EV-1-VERIFY-ALIGN.md`](./EV-1-VERIFY-ALIGN.md)

**交付物**：

- `mini_coding_agent/modes/graph/nodes/verify.py`
- `tests/test_harness_verify_align.py`（或扩展现有测）
- `eval/run_eval.py`（终判对齐部分）
- `docs/feedback/EV-1-VERIFY-ALIGN.md`

**验收门槛**：

- 有 `tests/` 时 harness verify 跑 pytest，不以 py_compile 替代
- 错误修复时 harness verify **fail**（非仅 expect_files）
- 测试文件被改则 fail
- `python eval/run_eval.py --fake` 全绿
- pytest + ruff 不低于基线

**回报后**：用户将 `feedback/EV-1-VERIFY-ALIGN.md` 带回主 Agent 验收；通过后方可开 Wave 2。

---

## 3. Wave 2 — EV-1 通过后并行派

| TASK_ID | 任务单 | 核心交付 |
|---------|--------|----------|
| EV-2-GRADING-SCHEMA | [EV-2-GRADING-SCHEMA.md](./EV-2-GRADING-SCHEMA.md) | `tier` / `grading` / `lock_tests` + tasks 迁移 |
| EV-3-GENERATE-ROBUST | [EV-3-GENERATE-ROBUST.md](./EV-3-GENERATE-ROBUST.md) | protocol/generate 容错 + live 复跑摘要 |

**并行冲突注意**：EV-2 可能改 `eval/run_eval.py`；EV-3 改 `protocol.py` / `generate.py` — **通常无冲突，可双窗口并行**。

---

## 4. 子 Agent 开场白（复制即用）

### Wave 1 — EV-1

```
你是本子项目的子 Agent，任务 EV-1-VERIFY-ALIGN。

请先阅读：
- @docs/struct/eval-repair-plan.md（§5.1）
- @docs/command/EV-1-VERIFY-ALIGN.md
- @docs/feedback/GL-5-LIVE-EVAL.md（off_by_one_sum 案例）

严格执行任务单：对齐 harness verify 与 eval 终判；修复假阳性；实现 lock_tests 基础行为。
禁止改 Gate、Locate、Generate（verify 调用链除外）。不新增 pip 依赖。

完成后写入 docs/feedback/EV-1-VERIFY-ALIGN.md（含方案摘要、验收自证、完整 pytest/ruff 输出）。
```

### Wave 2 — EV-2（EV-1 通过后）

```
你是子 Agent，任务 EV-2-GRADING-SCHEMA。
阅读 @docs/struct/eval-repair-plan.md §3、§5.2 与 @docs/command/EV-2-GRADING-SCHEMA.md。
依赖 EV-1 已验收。交付 grading schema + tasks 迁移 + eval/README。
回报 docs/feedback/EV-2-GRADING-SCHEMA.md。
```

### Wave 2 — EV-3（EV-1 通过后，可与 EV-2 并行）

```
你是子 Agent，任务 EV-3-GENERATE-ROBUST。
阅读 @docs/struct/eval-repair-plan.md §5.3 与 @docs/command/EV-3-GENERATE-ROBUST.md。
针对 live 失败模式增强 protocol/generate；须 pytest 回归 + feedback 含 live 复跑摘要。
回报 docs/feedback/EV-3-GENERATE-ROBUST.md。
```

---

## 5. 冻结清单（波次 C 期间）

不主动迭代（除非 EV 任务单明确允许）：Hook 体系 · Skill · 非 fix_bug 四类模板 live · Gate 规则化 · SWE-bench 接入。

---

*EVAL-REPAIR-DISPATCH · 主 Agent · 2026-06-05*
