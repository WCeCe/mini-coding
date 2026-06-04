# Phase 5 — Graph 编排（确定性 DAG）

> **状态**：✅ **Phase 5 结项**（P5.1–P5.6 + 黄金闭环 GL-1–GL-5 · 2026-06-04）· 5.8+ 优化按需迭代  
> **前置**：Phase 1 ✅ · Phase 2 ✅ · Phase 3 ✅ · Phase 4 ✅ · Agent 重构 R1–R4 ✅  
> **派活索引**：[`command/PHASE5-OVERVIEW.md`](../command/PHASE5-OVERVIEW.md) · 黄金闭环 [`GOLDEN-LOOP-OVERVIEW.md`](../command/GOLDEN-LOOP-OVERVIEW.md)  
> **验收**：[`feedback/P5-REVIEW.md`](../feedback/P5-REVIEW.md) · [`feedback/GL-REVIEW.md`](../feedback/GL-REVIEW.md)

---

## 1. 阶段目标

### 1.1 全貌

```
【离线】仓库 → index/ 代码图谱（ast + SQLite）
【在线 · graph mode · --harness on】
  用户消息
    → Gate（1× LLM 意图分类）
    → Planner（意图 → 静态 DAG 模板 + 槽位）
    → Executor（按节点拓扑执行；LLM 仅在指定节点）
    → verify 闭环 [→ review，按模板]
【降级】confidence=low / 流水线失败 → modes/open · ask()
【度量】eval/ 任务集 + FakeModel 回归 + 可选 --live Ollama
```

**面试叙事**：小模型不做调度器；**本地 LLM 只做 Gate 与节点工位**。编排由模板 DAG + 执行引擎完成；离线图谱缩小改动范围；改码走 governance；不确定则降级 open loop。

**与 Phase 1–4**：Graph 为编排壳；治理 / Hook / Skill / `make_plan` / `delegate` **复用** `platform/`。

### 1.2 交付范围（两波）

| 波次 | 内容 | 状态 |
|------|------|------|
| **5.1–5.6** | Gate、五类模板、通用 Executor、index、五类 FakeModel E2E、session 字段 | ✅ MVP 2026-06-03 |
| **GL-1–GL-5** | eval 基础设施、Locate snippet、Verify 错误摘要、fix_bug 瘦模板、live 基线 | ✅ 2026-06-04 |
| **目录重组** | `platform/` · `modes/open` · `modes/graph` · `index/` | ✅ 2026-06-04 |

### 1.3 能力矩阵

| 能力 | 要求 | 状态 |
|------|------|------|
| Gate | LLM 五类封闭标签 + low→open | ✅ |
| 编排 | `handle_ask`；`--harness on` | ✅ |
| 意图 | `generate_code` · `fix_bug` · `refactor` · `explain` · `project_ops` | ✅ 模板齐套 |
| Executor | 拓扑排序 + verify→generate retry | ✅ |
| index | `rig build`；Locate 优先图谱 | ✅ |
| eval | `eval/run_eval.py`；Fake 5/5；live 基线 2/5 | ✅ 基线已记录 |
| 降级 | 保留 open loop | ✅ |

**5.8+（非结项条件）**：规则 Gate、增量 index、混合检索、第六类意图、Graphviz、更大 benchmark 等。

---

## 2. 设计原则

| # | 原则 |
|---|------|
| 1 | 确定性编排为主（引擎推 DAG，非 LLM 逐步选 tool） |
| 2 | LLM 为受控组件（Gate、generate、review 等槽位） |
| 3 | 模板 DAG + 槽位；禁止 LLM 动态生成整张依赖图 |
| 4 | 能力意图 × 领域 Skill 正交 |
| 5 | 本地不出网（Ollama + 本地 index） |
| 6 | 先 MVP 跑通，再 eval 驱动迭代 |
| 7 | 铁律见 [`01-vision-and-roadmap.md`](./01-vision-and-roadmap.md) §5 |

---

## 3. 代码架构

整包 = coding harness；Graph 是其中一种 **mode**。

```
mini_coding_agent/
  cli.py
  platform/                 # 共用底座
    tools/ · hooks/ · governance.py · protocol.py · session.py · models.py · …
  modes/
    open/                   # Open Loop：MiniAgent · ask()
      agent.py · prompt.py
    graph/                  # Graph 编排（本 Phase 核心）
      runner.py · gate.py · planner.py · executor.py · pipeline.py
      nodes/ · templates/
  index/                    # 离线索引（CLI 仍称 rig build）
    build.py · query.py · store.py
eval/
  tasks.json · run_eval.py
```

| 模块 | 路径 |
|------|------|
| 入口 | `modes/graph/runner.py` · `handle_ask` |
| Gate | `modes/graph/gate.py` |
| 降级 | `modes/open/agent.py` · `ask()` |
| 治理 | `platform/governance.py` |

详见 [`02-codebase-reference.md`](./02-codebase-reference.md)。

---

## 4. 子阶段路线图（5.1 → 5.6）

```text
5.1 Gate + Runner + open 降级
  ↓
5.2 五类模板 + Planner + 槽位
  ↓
5.3 节点 + fix_bug 首条 E2E
  ↓
5.4 index 离线图谱 + Locate 接入
  ↓
5.5 通用 Executor + 五类 FakeModel E2E + Skill
  ↓
5.6 会话字段 + 文档 + P5-REVIEW
  ↓
GL-1–GL-5 eval 驱动黄金闭环（§7）
  ↓
5.8+ 优化（按需）
```

| 顺序 | 子阶段 | 任务单 | feedback |
|------|--------|--------|----------|
| 1 | 5.1 | [`P5.1-HARNESS-ENTRY`](../command/P5.1-HARNESS-ENTRY.md) | [`P5.1-HARNESS-ENTRY`](../feedback/P5.1-HARNESS-ENTRY.md) |
| 2 | 5.2 | [`P5.2-TEMPLATES-PLANNER`](../command/P5.2-TEMPLATES-PLANNER.md) | [`P5.2-TEMPLATES-PLANNER`](../feedback/P5.2-TEMPLATES-PLANNER.md) |
| 3 | 5.3 | [`P5.3-FIX-BUG-PIPELINE`](../command/P5.3-FIX-BUG-PIPELINE.md) | [`P5.3-FIX-BUG-PIPELINE`](../feedback/P5.3-FIX-BUG-PIPELINE.md) |
| 4 | 5.4 | [`P5.4-RIG`](../command/P5.4-RIG.md) | [`P5.4-RIG`](../feedback/P5.4-RIG.md) |
| 5 | 5.5 | [`P5.5-FIVE-INTENTS`](../command/P5.5-FIVE-INTENTS.md) | [`P5.5-FIVE-INTENTS`](../feedback/P5.5-FIVE-INTENTS.md) |
| 6 | 5.6 | [`P5.6-SESSION`](../command/P5.6-SESSION.md) | [`P5.6-SESSION`](../feedback/P5.6-SESSION.md) |
| — | 文档 | [`P5-DOCS`](../command/P5-DOCS.md) | [`P5-DOCS`](../feedback/P5-DOCS.md) |
| — | 验收 | [`P5-REVIEW`](../command/P5-REVIEW.md) | [`P5-REVIEW`](../feedback/P5-REVIEW.md) |

各子阶段详细交付表见 [`command/PHASE5-OVERVIEW.md`](../command/PHASE5-OVERVIEW.md)（历史规划与任务单保持一致）。

---

## 5. Gate 与五类意图

### 5.1 意图列表（封闭 · 仅此 5 个）

| intent_id | 含义 | 典型用户话 | 模板 |
|-----------|------|------------|------|
| `generate_code` | 新增/实现代码 | 「实现…」「写测试」 | `generate_code.json` |
| `fix_bug` | 修复错误 | 「报错」「测试失败」 | `fix_bug.json` |
| `refactor` | 不改语义改结构 | 「重构」「抽函数」 | `refactor.json` |
| `explain` | 只读解释 | 「什么意思」 | `explain.json` |
| `project_ops` | 项目操作 | 「跑 pytest」 | `project_ops.json` |

**边界**：要改文件 → generate/fix/refactor；只问不改 → explain；跑命令不改码 → project_ops。

**非法 intent** → `confidence=low` → open。

### 5.2 路由

| 条件 | route |
|------|-------|
| `confidence=high` 且 intent∈五类 | `harness_pipeline` |
| `confidence=low` 或非法 intent | `open` |
| 流水线异常 / verify 重试耗尽 | fallback `open` |

CLI：`--harness on|off` · `--gate-log`（仅观测 Gate）。

---

## 6. DAG 模板与节点

### 6.1 模板拓扑

| 模板 | 节点链 |
|------|--------|
| `generate_code` | locate → generate → verify → review |
| `fix_bug` | locate → generate → verify（黄金路径 **无 review**） |
| `refactor` | locate → plan → generate → verify → review |
| `explain` | locate → explain |
| `project_ops` | locate → ops → review |

`fix_bug` 当前 JSON（verify 失败 retry generate ≤2）：

```json
{
  "intent_id": "fix_bug",
  "nodes": [
    {"id": "locate", "type": "locate", "deps": []},
    {"id": "generate", "type": "generate", "deps": ["locate"]},
    {"id": "verify", "type": "verify", "deps": ["generate"]}
  ],
  "retry": {"verify": {"on_fail": "generate", "max": 2}}
}
```

### 6.2 槽位（MVP）

| 槽位 | 来源 |
|------|------|
| `goal` | 用户消息截断 |
| `files_hint` | traceback / 正则 / index |
| `symbols_hint` | 报错 / index |
| `skill_name` | Gate JSON |
| `test_command` | 检测 pytest |
| `ops_allowlist` | project_ops 专用 |

### 6.3 节点类型

| type | LLM | risky | 用于意图 |
|------|-----|-------|----------|
| locate | 否 | 否 | 五类 |
| generate | 是 | 是 | generate_code, fix_bug, refactor |
| verify | 否 | 否* | 三类改码 |
| review | 是 | 否 | 改码三类 + project_ops |
| plan | 是 | 否 | refactor |
| explain | 是 | 否 | explain |
| ops | 否 | 是* | project_ops |

\* verify/ops 的 risky 指 shell。

### 6.4 稳定性说明

| 范围 | FakeModel pytest | live eval | 迭代策略 |
|------|------------------|-----------|----------|
| `fix_bug` 黄金路径 | ✅ | 基线 2/5 | **可继续迭代** |
| 其余四类模板 | ✅ E2E | 未测 | ⏸ 保留，暂不派活 |

---

## 7. 黄金闭环与 Eval

Phase 5 第二波：在模块齐套后，用 **eval 驱动** 验证真实 `fix_bug` 能力。

### 7.1 黄金五步

```
用户消息 → handle_ask(harness_enabled=True)
  → Gate：fix_bug + high
  → Locate：≥1 段带行号源码 snippet（无 LLM）
  → Generate：1× LLM → patch/write（governance）
  → Verify：py_compile 或 pytest
  → 返回（verify 通过即成功；失败 retry generate ≤2）
```

### 7.2 GL 子任务（已结项）

| ID | 目标 | feedback |
|----|------|----------|
| GL-1 | eval 基础设施 | [`GL-1-EVAL-INFRA`](../feedback/GL-1-EVAL-INFRA.md) |
| GL-2 | Locate snippet 加固 | [`GL-2-LOCATE-SNIPPETS`](../feedback/GL-2-LOCATE-SNIPPETS.md) |
| GL-3 | Verify 错误摘要 | [`GL-3-VERIFY-ERROR-FORMAT`](../feedback/GL-3-VERIFY-ERROR-FORMAT.md) |
| GL-4 | fix_bug 去 review | [`GL-4-FIX-BUG-SLIM`](../feedback/GL-4-FIX-BUG-SLIM.md) |
| GL-5 | live Ollama 基线 | [`GL-5-LIVE-EVAL`](../feedback/GL-5-LIVE-EVAL.md) |
| GL-REVIEW | 总验收 | [`GL-REVIEW`](../feedback/GL-REVIEW.md) |

派活：[`GOLDEN-LOOP-OVERVIEW.md`](../command/GOLDEN-LOOP-OVERVIEW.md)。

### 7.3 Eval 用法

```bash
python eval/run_eval.py --fake          # CI / 回归，须 5/5
python eval/run_eval.py --live          # 真实 Ollama 基线
python eval/run_eval.py --fake --task nameerror_calc
```

契约与字段：[`eval/README.md`](../../eval/README.md)。

**tasks.json 字段**：`id` · `message` · `setup_files` · `expect_files` · `verify` · `harness_intent`（当前仅 `fix_bug`）。

### 7.4 Eval 工作流

```
1. --fake 全绿 → 2. --live 记失败步 → 3. 只改对应节点/模板
→ 4. 再跑对比 → 5. 通过率达标后再扩展其他意图
```

**stderr 定位**：

| 模式 | 失败步 |
|------|--------|
| `confidence=low` / `route=open` | Gate |
| `locate fail` | Locate |
| `generate 须返回 tool` | Generate |
| `verify fail` | Verify 或 Generate |
| `内容与期望不符` | expect_files（post_check） |

### 7.5 冻结清单（GL 期间有效，结项后仍建议遵守）

不主动迭代（除非阻塞 fix_bug）：Hook 体系 · Skill · 非 fix_bug 四类模板 · index 增量 · Gate 规则增强 · 第六类意图。

---

## 8. Phase 5 结项 Done Definition

### 8.1 模块交付（P5.1–5.6）

1. `--harness on`：五类意图各 ≥1 条 graph E2E pytest（FakeModel）。  
2. 每 ask 1 次 Gate；仅五类之一或 low→open。  
3. `rig build` 可用；Locate 使用 index。  
4. generate 走 governance；verify 失败可 retry。  
5. README + struct 标明 MVP vs 5.8+；P5-REVIEW 通过。  
6. 全量 pytest + ruff 不低于 Phase 4 基线。

### 8.2 黄金闭环（GL-1–5）

1. `eval/run_eval.py` FakeModel 全 task pass。  
2. live Ollama ≥1 task pass，失败有可追溯日志（当前 **2/5**）。  
3. Locate 产出含源码 snippet（有/无 index.db）。  
4. verify retry 使用格式化错误摘要。  
5. fix_bug 不依赖 review LLM。  
6. GL 期间 Hook/Skill/非 fix_bug 意图零迭代。

---

## 9. 5.8+ 优化路线

| 编号 | 方向 |
|------|------|
| 5.8 | Gate 混合（规则 + LLM） |
| 5.9 | index 增量 rebuild |
| 5.10 | 检索增强（邻居 + 关键词） |
| 5.11 | 第六类意图 / 领域子模板 |
| 5.12 | Graphviz DAG 导出 |
| 5.13 | eval 任务集扩展（15–20 条）· generate 鲁棒性 |

---

## 10. 风险登记

| 风险 | 缓解 |
|------|------|
| Gate 混类 | gate_prompt 边界表；FakeModel 边界用例 |
| Generate 格式 / patch 失败 | live 主瓶颈；解析容错 + retry（5.8+） |
| Fake 5/5 自嗨 | 必须对照 live 基线 |
| explain/ops 误写盘 | explain 禁工具；ops 白名单 |
| eval expect_files vs harness verify 双标准 | 文档说明；后续结构化报告 |

---

## 11. 已对齐产品决策

| # | 决策 |
|---|------|
| 1 | Gate 首版 = LLM；意图封闭 5 类 |
| 2 | DAG = 静态模板 + 槽位 |
| 3 | low / 非法 / 流水线失败 → open |
| 4 | index 纳入 MVP；语言 MVP = Python |
| 5 | 保留 `ask()`；整包 harness，graph 为一种 mode |
| 6 | eval 驱动 fix_bug；其余意图 FakeModel 覆盖、live 暂缓 |

---

*Phase 5 · phase5-graph · 2026-06-04*
