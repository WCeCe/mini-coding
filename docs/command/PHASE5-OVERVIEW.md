# Phase 5 派活总览（Graph MVP · 5.1–5.6）

> **struct 契约**：[`struct/phase5-graph.md`](../struct/phase5-graph.md) §4–§6（本文件为历史派活索引，Phase 5 已结项）。  
> **eval / 黄金闭环派活**：[`GOLDEN-LOOP-OVERVIEW.md`](./GOLDEN-LOOP-OVERVIEW.md) · struct §7。

---

## 1. 阶段目标

交付 **Graph Harness**：本地、不出网；**LLM 仅做意图分类与节点工位**；**模板 DAG + 执行引擎** 编排；**五类意图各一套模板**；**RIG** 离线建图；失败降级 **open**（现有 `ask()`）。

---

## 2. 封闭意图与模板（全员不得增删）

| intent_id | MVP 模板 |
|-----------|----------|
| `generate_code` | `templates/generate_code.json` |
| `fix_bug` | `templates/fix_bug.json` |
| `refactor` | `templates/refactor.json` |
| `explain` | `templates/explain.json` |
| `project_ops` | `templates/project_ops.json` |

Gate **仅此 5 个** `intent_id`；非法或 `confidence=low` → `open`。

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 依赖 | 标准库 + 已有 **PyYAML** + pytest；**不新增** pip 依赖（含 chromadb、tree-sitter、graphviz） |
| 编排 | **禁止** LLM 动态生成整张 DAG；拓扑来自 JSON 模板 |
| 改码 | `write_file` / `patch_file` **必须**经现有 `run_tool` → governance |
| Hook | Phase 2 observe-only、fail-open **不变**（除非 5.6 明确只加 observe 的 node 钩子） |
| 降级 | **必须**保留 `agent.ask()`；禁止 Harness 为唯一入口 |
| 注释 | 铁律 §7 |
| 文案 | 铁律 §8；Gate/节点错误与 stderr 中文；JSON 字段名英文 |
| 测试 | 新逻辑 pytest；**Gate 与 E2E 禁止依赖真实 Ollama**（`FakeModelClient`） |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| Git | 不 commit / push（除非用户明确要求） |

---

## 4. 子阶段与任务单（派活顺序）

| 子阶段 | TASK_ID | 任务单 | 可以写代码 | 依赖 |
|--------|---------|--------|------------|------|
| **5.1** | P5.1-HARNESS-ENTRY | [P5.1-HARNESS-ENTRY](./P5.1-HARNESS-ENTRY.md) | 是 | — |
| **5.2** | P5.2-TEMPLATES-PLANNER | [P5.2-TEMPLATES-PLANNER](./P5.2-TEMPLATES-PLANNER.md) | 是 | 5.1 |
| **5.3** | P5.3-FIX-BUG-PIPELINE | [P5.3-FIX-BUG-PIPELINE](./P5.3-FIX-BUG-PIPELINE.md) | 是 | 5.2 |
| **5.4** | P5.4-RIG | [P5.4-RIG](./P5.4-RIG.md) | 是 | 5.3（Locate 接口） |
| **5.5** | P5.5-FIVE-INTENTS | [P5.5-FIVE-INTENTS](./P5.5-FIVE-INTENTS.md) | 是 | 5.3–5.4 |
| **5.6** | P5.6-SESSION | [P5.6-SESSION](./P5.6-SESSION.md) | 是 | 5.5 |
| 文档 | P5-DOCS | [P5-DOCS](./P5-DOCS.md) | 否 | 5.5 |
| 验收 | P5-REVIEW | [P5-REVIEW](./P5-REVIEW.md) | 否 | 5.6 + P5-DOCS |

**禁止跳阶段**：未验收上一子阶段 feedback 前，不派下一任务（主 Agent 复审后派活）。

---

## 5. 里程碑

| 标记 | 子阶段 | 标志 |
|------|--------|------|
| M1 | 5.1 | Gate pytest；`--gate-log` 可见 intent |
| M2 | 5.2 | 五模板 + Planner 五类单测 |
| M3 | 5.3 | `fix_bug` harness E2E（FakeModel） |
| M4 | 5.4 | `rig build` + locate 用图谱 |
| M5 | 5.5 | 五类意图 E2E 全绿 |
| M6 | 5.6 + REVIEW | Phase 5 MVP 结项（struct §11） |

---

## 6. 子 Agent 窗口开场白（按子阶段复制）

### 5.1

```
你是本子项目的子 Agent（执行者）。
请先读：
- @docs/command/PHASE5-OVERVIEW.md
- @docs/command/P5.1-HARNESS-ENTRY.md
- @docs/struct/phase5-graph.md（§5.1、§5 意图表）

在约束内自行设计并实现；回报写入 docs/feedback/P5.1-HARNESS-ENTRY.md。
```

### 5.2

```
请先读：@docs/command/PHASE5-OVERVIEW.md、@docs/command/P5.2-TEMPLATES-PLANNER.md、@docs/struct/phase5-graph.md（§6 模板）
依赖：feedback/P5.1-HARNESS-ENTRY.md 已验收。
回报：docs/feedback/P5.2-TEMPLATES-PLANNER.md
```

### 5.3

```
请先读：@docs/command/P5.3-FIX-BUG-PIPELINE.md、@docs/struct/phase5-graph.md（§7 节点）
依赖：P5.2 已验收。
回报：docs/feedback/P5.3-FIX-BUG-PIPELINE.md
```

### 5.4

```
请先读：@docs/command/P5.4-RIG.md、@docs/struct/phase5-graph.md（5.4）
依赖：P5.3 已验收。
回报：docs/feedback/P5.4-RIG.md
```

### 5.5

```
请先读：@docs/command/P5.5-FIVE-INTENTS.md、@docs/struct/phase5-graph.md（§5.1 五类、§7）
依赖：P5.3、P5.4 已验收。
回报：docs/feedback/P5.5-FIVE-INTENTS.md
```

### 5.6 / 文档 / 验收

```
P5.6：@docs/command/P5.6-SESSION.md → feedback/P5.6-SESSION.md
P5-DOCS：@docs/command/P5-DOCS.md → feedback/P5-DOCS.md
P5-REVIEW：@docs/command/P5-REVIEW.md → feedback/P5-REVIEW.md（须等 DOCS + 5.6）
```

---

## 7. Out of Scope（所有子阶段）

- LLM 动态规划 DAG、第六类意图、chromadb、tree-sitter、git worktree、benchmark、替换 `ask()` 唯一入口

---

*Phase 5 派活索引 · 主 Agent 维护*
