# 黄金闭环 — 派活总览（Phase 5 波次 B）

> **struct 契约**：[`struct/phase5-graph.md`](../struct/phase5-graph.md) §7  
> **前置**：Phase 5 Graph MVP（5.1–5.6）✅  
> **状态**：✅ 已结项（GL-REVIEW 2026-06-04）· 本文件保留作派活历史索引。

---

## 1. 当前优先级

| 优先级 | 说明 |
|--------|------|
| **P0** | GL-1 → GL-5 → GL-REVIEW（顺序执行） |
| **冻结** | Hook 增强、Skill 绑定、explain/ops/refactor/generate_code 模板、RIG 增量、Gate 规则化 |
| **暂缓** | benchmark 大盘、Phase 5.7+、默认 `--harness on`（GL-5 文档约定即可） |

---

## 2. 任务单（严格顺序）

| 顺序 | TASK_ID | 任务单 | 可以写代码 | 依赖 | 状态 |
|------|---------|--------|------------|------|------|
| 1 | **GL-1** | [GL-1-EVAL-INFRA](./GL-1-EVAL-INFRA.md) | 是 | — | ✅ 通过 |
| 2 | **GL-2** | [GL-2-LOCATE-SNIPPETS](./GL-2-LOCATE-SNIPPETS.md) | 是 | GL-1 | ✅ 通过 |
| 3 | **GL-3** | [GL-3-VERIFY-ERROR-FORMAT](./GL-3-VERIFY-ERROR-FORMAT.md) | 是 | GL-1 | ✅ 通过 |
| 4 | **GL-4** | [GL-4-FIX-BUG-SLIM](./GL-4-FIX-BUG-SLIM.md) | 是 | GL-1 | ✅ 通过 |
| 5 | **GL-5** | [GL-5-LIVE-EVAL](./GL-5-LIVE-EVAL.md) | 是* | GL-1–4 | ✅ 通过 |
| 6 | **GL-REVIEW** | [GL-REVIEW](./GL-REVIEW.md) | 否 | GL-5 | ✅ **结项** |

**主 Agent 派活令**：[`GOLDEN-LOOP-DISPATCH.md`](./GOLDEN-LOOP-DISPATCH.md)

\* GL-5 含真实 Ollama 手动跑；代码改动限于 eval 与文档，不要求一次修通所有 live 任务。

**并行说明**：GL-2 / GL-3 / GL-4 均依赖 GL-1，彼此可并行派给不同子 Agent，但 **GL-5 必须等 GL-2–4 全部 feedback 验收通过**。

---

## 3. 工程规范（全员）

| 规范 | 要求 |
|------|------|
| 范围 | **仅** fix_bug 黄金路径 + eval；见 struct §7.5 冻结清单 |
| 依赖 | 不新增 pip 包 |
| 改码 | patch/write 经 `run_tool` → governance |
| Hook | **不修改**（eval 测试可 `enable_trace_hook=False`） |
| 测试 | 新逻辑 pytest；框架测 FakeModel；live eval 单独文档 |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| 回报 | `feedback/<TASK_ID>.md`（方案摘要 + 验收自证 + pytest/ruff 输出） |
| Git | 不 commit / push（除非用户明确要求） |

---

## 4. 里程碑

| 标记 | 任务 | 标志 |
|------|------|------|
| M0 | GL-1 | `eval/run_eval.py --fake` 1 task pass |
| M1 | GL-2 | Locate 无/有 rig 均产出源码 snippet |
| M2 | GL-3 | verify retry prompt 含错误摘要 |
| M3 | GL-4 | fix_bug 无 review LLM 仍可完成 |
| M4 | GL-5 | 真实 Ollama ≥1 task pass + 失败日志归档 |
| M5 | GL-REVIEW | struct Done Definition §11 全勾选 |

---

## 5. 子 Agent 开场白（复制即用）

### GL-1

```
你是子 Agent，任务 GL-1-EVAL-INFRA。
阅读 docs/struct/phase5-graph.md §7.2 GL-1 与 docs/command/GL-1-EVAL-INFRA.md。
交付 eval/tasks.json、eval/run_eval.py、tests/test_eval_runner.py、eval/README.md。
禁止改 Hook、Skill、非 fix_bug 模板。回报 docs/feedback/GL-1-EVAL-INFRA.md。
```

### GL-2

```
你是子 Agent，任务 GL-2-LOCATE-SNIPPETS。
阅读 docs/struct/phase5-graph.md §7.2 GL-2。
加固 harness/nodes/locate.py：RIG/search 命中须 read_file 产出源码 snippet。
依赖 GL-1 已验收。回报 docs/feedback/GL-2-LOCATE-SNIPPETS.md。
```

### GL-3

```
你是子 Agent，任务 GL-3-VERIFY-ERROR-FORMAT。
阅读 docs/struct/phase5-graph.md §7.2 GL-3。
新增 format_error_for_model，接入 executor verify 失败 → generate retry。
回报 docs/feedback/GL-3-VERIFY-ERROR-FORMAT.md。
```

### GL-4

```
你是子 Agent，任务 GL-4-FIX-BUG-SLIM。
阅读 docs/struct/phase5-graph.md §7.2 GL-4。
fix_bug 黄金路径 verify 通过即可返回，不依赖 review LLM。
同步 FakeModel 单测。回报 docs/feedback/GL-4-FIX-BUG-SLIM.md。
```

### GL-5

```
你是子 Agent，任务 GL-5-LIVE-EVAL。
阅读 docs/struct/phase5-graph.md §7.2 GL-5。
扩展 eval/tasks.json 至 3–5 任务；document --live Ollama 跑法。
诚实记录首次通过率与失败步，不伪造。回报 docs/feedback/GL-5-LIVE-EVAL.md。
```

---

## 6. 主 Agent 派活检查清单

- [ ] 只派 GL-1–5 之一，不夹带 Hook/Skill 需求
- [ ] 子 Agent 已读 `struct/phase5-graph.md`
- [ ] 上一任务 feedback 已验收再派下一任务（GL-2/3/4 除外可并行）
- [ ] GL-5 前确认 GL-2、GL-3、GL-4 均已 ✅

---

*command/GOLDEN-LOOP-OVERVIEW · 2026-06-04*
