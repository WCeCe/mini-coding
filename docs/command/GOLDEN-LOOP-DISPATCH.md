# 主 Agent 派活令 — 黄金闭环（Golden Loop）

> **发布者**：主 Agent  
> **发布日期**：2026-06-04  
> **契约**：[`struct/phase5-graph.md`](../struct/phase5-graph.md)  
> **任务索引**：[`GOLDEN-LOOP-OVERVIEW.md`](./GOLDEN-LOOP-OVERVIEW.md)

---

## 0. 战略对齐（全员必读）

Phase 5 Harness **模块已齐**；**黄金闭环已于 2026-06-04 结项**（见 [`feedback/GL-REVIEW.md`](../feedback/GL-REVIEW.md)）。后续迭代以 **eval 通过率** 为唯一优先级，不扩展 Hook/Skill/第六类意图。

---

## 1. 派活波次（禁止跳波）

| 波次 | 任务 | 条件 | 窗口数 |
|------|------|------|--------|
| **Wave 1** | GL-1-EVAL-INFRA | 立即派 | **1** |
| **Wave 2** | GL-2 + GL-3 + GL-4 | Wave 1 feedback **主 Agent 验收通过** | 最多 **3**（可并行） |
| **Wave 3** | GL-5-LIVE-EVAL | Wave 2 **全部**验收通过 | **1** |
| **Wave 4** | GL-REVIEW | Wave 3 feedback 提交 | 主 Agent 自审或独立 REVIEW 窗口 |

**当前状态（主 Agent 维护）**：

| TASK_ID | 波次 | 派活状态 | 验收状态 |
|---------|------|----------|----------|
| GL-1-EVAL-INFRA | 1 | ✅ 已派 | ✅ **通过**（2026-06-04） |
| GL-2-LOCATE-SNIPPETS | 2 | ✅ 已派 | ✅ **通过**（2026-06-04） |
| GL-3-VERIFY-ERROR-FORMAT | 2 | ✅ 已派 | ✅ **通过**（2026-06-04） |
| GL-4-FIX-BUG-SLIM | 2 | ✅ 已派 | ✅ **通过**（2026-06-04） |
| GL-5-LIVE-EVAL | 3 | ✅ 已派 | ✅ **通过**（2026-06-04 · live 2/5） |
| GL-REVIEW | 4 | ✅ 已派 | ✅ **黄金闭环结项** |

---

## 2. Wave 1 — 立即执行

### 任务：GL-1-EVAL-INFRA

**目标**：建立 eval 框架，使黄金闭环 **可被重复度量**。

**任务单**：[`GL-1-EVAL-INFRA.md`](./GL-1-EVAL-INFRA.md)

**交付物**（缺一不可）：

- `eval/tasks.json`（≥1 个 NameError 任务）
- `eval/run_eval.py`（含 `--fake`）
- `eval/README.md`
- `tests/test_eval_runner.py`
- `docs/feedback/GL-1-EVAL-INFRA.md`

**验收门槛**：

- `python -m pytest tests/test_eval_runner.py -q` 全绿
- `python eval/run_eval.py --fake` 对 tasks 至少 1/1 pass
- 全量 pytest + ruff 不低于派活前基线
- **未改动** hooks/、skills、Harness 业务节点（除非 GL-1 阻塞性 import 修复）

**回报后**：用户将 `feedback/GL-1-EVAL-INFRA.md` 带回主 Agent 窗口验收；通过后方可开 Wave 2。

---

## 3. Wave 2 — GL-1 通过后并行派

三个任务 **互不依赖**，可同时开三个子 Agent 窗口；**全部验收通过** 后方可派 GL-5。

| TASK_ID | 任务单 | 核心交付 |
|---------|--------|----------|
| GL-2-LOCATE-SNIPPETS | [GL-2-LOCATE-SNIPPETS.md](./GL-2-LOCATE-SNIPPETS.md) | Locate 产出 **源码 snippet**（RIG/search 命中须 read_file） |
| GL-3-VERIFY-ERROR-FORMAT | [GL-3-VERIFY-ERROR-FORMAT.md](./GL-3-VERIFY-ERROR-FORMAT.md) | `format_error_for_model` + executor 接入 |
| GL-4-FIX-BUG-SLIM | [GL-4-FIX-BUG-SLIM.md](./GL-4-FIX-BUG-SLIM.md) | fix_bug verify 通过即返回，**去掉 review LLM** |

**并行冲突注意**：

- GL-2 / GL-3 / GL-4 可能同改 `executor.py` 或 `fix_bug.json` — 若多窗口并行，**各子 Agent 只改自己任务单范围内的文件**；若冲突，主 Agent 指定 GL-4 最后合并 executor 的 `_resolve_final`。
- 推荐：GL-2、GL-3 并行；GL-4 在 GL-3 之后或单独窗口。

---

## 4. Wave 3 — GL-5-LIVE-EVAL

**前置**：GL-1～GL-4 feedback 全部 **主 Agent 验收通过**。

**目标**：3–5 个 eval 任务 + `--live` Ollama 文档与 **诚实** 首次基线报告。

**允许**：live 通过率 <100%；feedback 必须逐步定位 Gate/Locate/Generate/Verify。

---

## 5. Wave 4 — GL-REVIEW

主 Agent 对照 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §8 Done Definition 独立复审；更新 [`struct/README.md`](../struct/README.md) 状态板。

---

## 6. 子 Agent 窗口开场白（复制到新对话）

见 [`GOLDEN-LOOP-OVERVIEW.md`](./GOLDEN-LOOP-OVERVIEW.md) §5，或下文 **附录 A**。

---

## 附录 A — Wave 1 开场白（GL-1，立即复制）

```
你是本子项目的子 Agent，执行主 Agent 派发的任务 GL-1-EVAL-INFRA。

请先阅读（按顺序）：
1. @docs/struct/phase5-graph.md — 全文，重点 §7.2 GL-1、§7.3 tasks.json 格式、§7.5 冻结清单
2. @docs/command/GL-1-EVAL-INFRA.md — 本任务目标、约束、验收
3. @docs/struct/03-collaboration-model.md — 子 Agent 边界
4. @docs/feedback/TEMPLATE.md — 回报格式

你的任务：
建立 eval 基础设施，使 fix_bug 黄金闭环可被 FakeModel 重复度量。

必须交付：
- eval/tasks.json（至少 1 个 nameerror_calc 类任务）
- eval/run_eval.py（支持 --fake；为后续 --live 留扩展位）
- eval/README.md
- tests/test_eval_runner.py
- docs/feedback/GL-1-EVAL-INFRA.md

硬性约束：
- 不修改 Hook、Skill、Gate/Locate/Generate/Verify 业务逻辑
- 不新增 pip 依赖
- eval 调用 handle_ask(..., harness_enabled=True)，Agent 用 approval_policy=auto
- 铁律 §6–§8；完成后跑 pytest + ruff，回报中贴完整输出

完成后只写入 feedback/GL-1-EVAL-INFRA.md，等待主 Agent 验收。不要自行派下一阶段任务。
```

---

## 附录 B — Wave 2 开场白（GL-1 通过后分别复制）

### GL-2

```
你是子 Agent，任务 GL-2-LOCATE-SNIPPETS。主 Agent 已验收 GL-1 通过。

阅读：@docs/struct/phase5-graph.md §7.2 GL-2、@docs/command/GL-2-LOCATE-SNIPPETS.md

加固 Locate：RIG/search 命中必须 read_file 产出带行号的源码 snippet；Locate 禁止 LLM。
回报：docs/feedback/GL-2-LOCATE-SNIPPETS.md
禁止改 Hook/Skill/非 fix_bug 模板。
```

### GL-3

```
你是子 Agent，任务 GL-3-VERIFY-ERROR-FORMAT。主 Agent 已验收 GL-1 通过。

阅读：@docs/struct/phase5-graph.md §7.2 GL-3、@docs/command/GL-3-VERIFY-ERROR-FORMAT.md

实现 format_error_for_model，verify 失败摘要写入 ctx.last_verify_error 供 Generate retry。
回报：docs/feedback/GL-3-VERIFY-ERROR-FORMAT.md
```

### GL-4

```
你是子 Agent，任务 GL-4-FIX-BUG-SLIM。主 Agent 已验收 GL-1 通过。

阅读：@docs/struct/phase5-graph.md §7.2 GL-4、@docs/command/GL-4-FIX-BUG-SLIM.md

fix_bug 黄金路径 verify 通过即返回，不依赖 review LLM；同步 FakeModel 单测。
回报：docs/feedback/GL-4-FIX-BUG-SLIM.md
```

---

## 附录 C — Wave 3 开场白（GL-5）

```
你是子 Agent，任务 GL-5-LIVE-EVAL。主 Agent 已验收 GL-1～GL-4 全部通过。

阅读：@docs/struct/phase5-graph.md §7.2 GL-5、§7、@docs/command/GL-5-LIVE-EVAL.md

扩展 eval/tasks.json 至 3–5 任务；实现 --live Ollama；诚实记录首次通过率与失败步。
回报：docs/feedback/GL-5-LIVE-EVAL.md（必须含真实 --live 跑结果，可部分 fail）
```

---

*主 Agent 派活令 · 更新验收状态见上表*
