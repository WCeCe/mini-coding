# Eval 架构体检计划（波次 D）

> **状态**：✅ **结项**（2026-06-05 · 波次 D P0–P2 验收）  
> **前置**：Phase 5 + 黄金闭环 GL-1–5 ✅ · Eval 波次 C（EV-1–7）✅  
> **触发原因**：对照 [KWCode](https://github.com/zou0613/KWCode) eval 体系审计——现有 `eval/` 能测「结果对不对」，不能系统性地测「harness 哪一环是架构痛点」  
> **参考**：[`eval-repair-plan.md`](./eval-repair-plan.md)（波次 C · 评分与 verify 对齐）· [`phase5-graph.md`](./phase5-graph.md) §7  
> **展开文档**：[`docs/eval/README.md`](../eval/README.md)（五层体系 · schema · 逐步清单 · 路线图）

---

## 1. 问题陈述

波次 C 后，`eval/` 已具备 `grading` / `lock_tests` / verify 对齐 / 15 条任务 / 基线对比。但仍存在**架构评测缺口**：

| 发现 | 严重度 | 说明 |
|------|--------|------|
| eval 终判只看磁盘 + pytest，**不读 session** | P0 | `last_gate` / `last_verify` / `harness_last_node` 已有，报告未用 |
| **无 `pipeline_ok` 与 `outcome_ok` 分拆** | P0 | open 降级或终判碰巧通过时，无法区分「管线成功 vs 仅结果对」 |
| 失败归因靠 stderr 正则，**无稳定 taxonomy** | P0 | 难做 E2E 分因与跨版本对比 |
| `tasks.json` 与 FakeModel 管线回归**脱节** | P0 | `test_harness_*` 手写场景，不读任务清单 |
| Locate **永远 ok=True**，eval 测不到定位质量 | P1 | 无 snippet 门槛（F4 类问题） |
| 任务集按**数量**扩展，未按**架构维度**覆盖 | P1 | 缺 retry / decoy / gate 边界 / 无 RIG 等专项 |
| 无踩坑固化流程 | P2 | 无 `test_discovered_bugs` / QA_LOG 循环 |

**本波次目标**：把 eval 从「结果探测器」升级为「**架构探测器 + 能力探针**」双层体系，参考 KWCode 的分层思路，但贴合本仓库 **Gate → slots → Locate → Generate → Verify → retry** 的 fix_bug DAG。

**产品决策（已对齐）**：

1. **不替换** `eval/run_eval.py` 主框架，在其上扩展报告与 schema。  
2. **不引入**新 pip 依赖。  
3. **接受** live 短期仍可能低分——报告必须能回答「该改哪个节点」。  
4. **分拆** CI 必跑的架构回归 vs 手动的 live 能力探针。

---

## 2. 目标与非目标

### 2.1 目标

| # | 目标 | 可验证标志 |
|---|------|------------|
| G1 | live eval 报告 **`pipeline_ok` + `failure_type` + session 观测** | `run_eval.py` JSON/Markdown 含新字段 |
| G2 | `tasks.json` 支持 **`architecture` 契约** + FakeModel 逐条回归 | `tests/test_eval_contract.py` 绿 |
| G3 | **slots / locate 量化诊断**（KWCode F3/F4 缩小版） | `tests/diagnostic/test_slots_locate.py` 准确率门槛 |
| G4 | **5 条架构维度 bench**（retry/decoy/gate/no-rig/…） | `eval/tasks/` 或 `tasks.json` 扩展 + 契约测 |
| G5 | **踩坑库 + QA_LOG 模板** | `tests/regression/test_discovered_bugs.py` + `docs/eval/QA_LOG.md` |
| G6 | Locate **无有效 snippet 时可 fail**（可选开关） | harness 行为 + 契约测 |

### 2.2 非目标

- 完整 KWCode GapDetector（11 类型）——仅 fix_bug 路径需要的精简 taxonomy  
- SWE-bench / Harbor / 新 pip 包  
- 非 `fix_bug` 意图 live 大盘  
- Gate 规则化混合（留给 5.8）  
- 飞轮 / Prompt Optimizer

---

## 3. 五层 eval 体系（本仓库映射）

对照 KWCode 四层，本仓库 fix_bug 黄金路径映射如下：

```
┌──────────────────────────────────────────────────────────────────┐
│ L1  组件诊断 pytest（CI 必绿，零 LLM）                            │
│     tests/diagnostic/ — Gate 解析、slots 提取、locate snippet…    │
├──────────────────────────────────────────────────────────────────┤
│ L2  契约 eval（CI 必绿，FakeModel + tasks.json）                  │
│     architecture 字段 + fake_script → pipeline_ok 断言          │
├──────────────────────────────────────────────────────────────────┤
│ L3  架构维度 bench（CI 或 nightly，FakeModel 为主，可选 live）     │
│     retry / decoy / gate / no-rig / multi-file 各 ≥1            │
├──────────────────────────────────────────────────────────────────┤
│ L4  Live 能力探针（手动，Ollama）                                 │
│     eval/run_eval.py — outcome_ok + failure_type + 框架/模型分因  │
├──────────────────────────────────────────────────────────────────┤
│ L5  踩坑流程（持续）                                              │
│     QA_LOG → test_discovered_bugs.py                            │
└──────────────────────────────────────────────────────────────────┘
```

| 层 | 回答的问题 | CI |
|----|------------|-----|
| L1 | 每个**节点本身**有没有 bug？ | ✅ |
| L2 | 任务设计的**管线契约**是否执行？ | ✅ |
| L3 | **架构维度**是否覆盖？ | 建议 ✅（FakeModel 部分） |
| L4 | 真实模型下 harness **够不够用**？ | ❌ 手动 |
| L5 | 漏洞是否**不再复发**？ | ✅（随踩坑增长） |

---

## 4. 失败 taxonomy（`failure_type`）

Live 与契约 eval 共用枚举（字符串值），用于 E2E 分因与基线对比。

| `failure_type` | 含义 | 建议优先改动 |
|----------------|------|--------------|
| `gate_low` | `confidence=low` 或 `route=open` | `gate.py` / `gate_prompt.py` |
| `gate_wrong_intent` | 非预期 `intent_id` | `gate.py` |
| `locate_no_snippet` | 无带行号源码 snippet | `locate.py` / `slots.py` |
| `locate_wrong_file` | 触及文件不在 `must_include_files` | `locate.py` / `index/` |
| `generate_protocol` | 未返回合法 `<tool>` | `protocol.py` |
| `generate_patch_match` | `old_text` 0 次/多次匹配 | `nodes/generate.py` |
| `generate_governance` | `run_tool` 治理拒绝 | `governance.py` |
| `verify_py_compile` | py_compile 失败 | generate / verify |
| `verify_pytest` | pytest 失败 | generate / verify retry |
| `verify_lock_tests` | 测试被改或新增 | `verify_rules.py` |
| `fallback_open` | 流水线失败且 open 降级 | `runner.py` + 上游节点 |
| `expect_files` | exact grading 终判不符 | 任务设计 / generate |
| `exception` | 未捕获异常 | 调用栈 |
| `outcome_ok` | 终判通过（仅 outcome 维） | — |
| `pipeline_ok` | 契约全满足（仅 pipeline 维） | — |
| `unknown` | 无法归类 | 补 taxonomy |

**推断顺序**（实现参考）：

1. 读 `agent.session`（`last_gate`、`last_verify`、`harness_last_node`、`last_files_touched`）  
2. 解析 stderr steps（现有 `parse_harness_steps`）  
3. 终判错误（grading / lock / verify）  
4. 回退 `unknown`

---

## 5. 报告字段契约（P0 · `run_eval.py`）

### 5.1 扩展 `TaskResult`

在现有 `TaskResult` / JSON 报告上增加：

```json
{
  "task_id": "import_chain_rate",
  "passed": false,
  "pipeline_ok": false,
  "outcome_ok": false,
  "failure_type": "locate_wrong_file",
  "failure_step": "locate",
  "observability": {
    "gate": {
      "intent_id": "fix_bug",
      "confidence": "high",
      "route": "harness_pipeline"
    },
    "last_verify": {
      "ok": false,
      "method": "shell",
      "summary": "pytest 失败…"
    },
    "harness_last_node": {
      "node_id": "verify",
      "type": "verify",
      "ok": false
    },
    "files_touched": ["app.py"],
    "open_fallback": false,
    "generate_attempts": 1
  },
  "steps": [ "..." ],
  "tier": "medium",
  "grading": "tests_only"
}
```

### 5.2 通过语义

| 字段 | 定义 |
|------|------|
| `outcome_ok` | 现有 `check_task_grading` 通过 |
| `pipeline_ok` | Gate 契约 + 未 open 降级 +（若任务有 `architecture`）契约断言全过 |
| `passed`（live 默认） | **`outcome_ok` 且非 `fallback_open`**；可选 `--strict-pipeline` 时要求 `pipeline_ok` |

### 5.3 session 读取点

`run_single_task` 在 `handle_ask` 返回后、终判前读取：

```python
agent.session.get("last_gate")
agent.session.get("last_verify")
agent.session.get("harness_last_node")
agent.session.get("last_files_touched")
```

stderr 中是否含 `降级 open` → `open_fallback`。

### 5.4 Done（P0）

- [ ] `TaskResult` / `task_result_to_dict` / Markdown·JSON 报告含新字段  
- [ ] `infer_failure_type(session, stderr, grading_err) -> str` 实现  
- [ ] `--strict-pipeline` 可选 CLI  
- [ ] `tests/test_eval_runner.py` 覆盖 taxonomy 推断（mock session，无 Ollama）  
- [ ] `eval/README.md` 更新「读报告」一节

---

## 6. `architecture` schema + 契约 pytest（P0）

### 6.1 `tasks.json` 扩展字段（向后兼容）

```json
{
  "id": "import_chain_rate",
  "tier": "medium",
  "grading": "tests_only",
  "message": "...",
  "setup_files": { "...": "..." },
  "verify": "pytest",
  "harness_intent": "fix_bug",
  "architecture": {
    "intent": "fix_bug",
    "gate": {
      "route": "harness_pipeline",
      "confidence": "high"
    },
    "pipeline_must_succeed": true,
    "no_open_fallback": true,
    "locate": {
      "must_include_files": ["rates.py"],
      "min_snippets_with_source_lines": 1
    },
    "verify": {
      "method": "pytest"
    },
    "generate_max_attempts": 2,
    "must_modify": ["rates.py"],
    "must_not_modify_prefixes": ["tests/"]
  },
  "fake_script": [
    {
      "gate": { "intent_id": "fix_bug", "confidence": "high" }
    },
    {
      "patch": {
        "path": "rates.py",
        "old_text": "return base * rate",
        "new_text": "return base * rate / 100"
      }
    }
  ]
}
```

| 字段 | 含义 |
|------|------|
| `architecture.gate` | 预期 Gate 结果（FakeModel live 均可用） |
| `pipeline_must_succeed` | harness 流水线 `PipelineResult.ok` |
| `no_open_fallback` | stderr 不得含「降级 open」 |
| `locate.must_include_files` | `last_files_touched` 或 locate output 须含 |
| `locate.min_snippets_with_source_lines` | 定位 snippet 质量（契约测用 mock locate 时可跳过 live） |
| `must_modify` | 终判时这些文件相对 setup 有变更 |
| `fake_script` | FakeModel 逐步队列；**仅 L2 契约测使用**，不改变 live 行为 |

缺省 `architecture` 的旧任务：仅跑现有 grading，不断言 `pipeline_ok`。

### 6.2 新增测试

```
tests/test_eval_contract.py
```

-  parametrized：凡含 `fake_script` 的任务  
- 流程：`setup_task_workspace` → `FakeModelClient(fake_script)` → `handle_ask(harness=True)` → 读 session → `assert_pipeline_contract(task, agent, stderr)`  
- 断言：`pipeline_ok == True`，`outcome_ok == True`

### 6.3 CI

在现有 `pytest` job 内增加（无新 job 亦可）：

```bash
python -m pytest tests/test_eval_contract.py tests/test_eval_runner.py -q
```

### 6.4 Done（P0）

- [ ] `eval/task_schema.py`（或 `run_eval.py` 内）解析/校验 `architecture`  
- [ ] `assert_pipeline_contract()` 实现  
- [ ] 至少 **3 条**现有任务补全 `architecture` + `fake_script`（建议：`nameerror_calc`、`off_by_one_sum`、`import_chain_rate`）  
- [ ] `test_eval_contract.py` 全绿

---

## 7. slots / locate 量化诊断（P1）

### 7.1 文件

```
tests/diagnostic/test_slots_locate.py
```

### 7.2 覆盖点

**slots（`fill_slots` / `extract_files_hint` / `extract_symbols_hint`）**

| 样本类 | 示例 | 期望 |
|--------|------|------|
| traceback 路径 | `File "calc.py", line 2` | `files_hint` 含 `calc.py` |
| 消息内路径 | `请修复 calc.py` | `files_hint` 含 `calc.py` |
| 无路径有符号 | `add(2,3) 得到 -1` | `symbols_hint` 含 `add` |
| 负例 | 纯 explain 问句 | 无误导性 `files_hint` |

**locate（`run_locate` + FakeModel 或纯规则）**

| 样本类 | 期望 |
|--------|------|
| 有 `files_hint` | snippets 含 `# file:` 行号 + 源码行 |
| 有 RIG | `used_rig=True` 时 snippet 非空 |
| decoy 目录（P1 bench 联动） | `must_include_files` 命中正确文件 |

### 7.3 成功标准（出厂条件缩小版）

| ID | 指标 | 门槛 |
|----|------|------|
| D1 | slots 文件提取准确率 | ≥ 90%（≥18/20 手工样本） |
| D2 | slots 符号提取准确率 | ≥ 85%（medium 任务相关样本） |
| D3 | locate snippet 含源码行比例 | 有 hint 时 **100%** |

### 7.4 Done（P1）

- [ ] `tests/diagnostic/` 目录 + `test_slots_locate.py`  
- [ ] 20+ slots 样本 parametrized  
- [ ] 与 `test_harness_locate_snippets.py` 不重复断言（diagnostic 偏**量化门槛**，harness 偏行为）

---

## 8. 五条架构维度 bench（P1）

在 `eval/tasks.json` 追加或 `eval/tasks/arch/` 目录化；每条须含 `architecture` + `fake_script` + `dimension` 标签。

| ID | `dimension` | 测的架构点 | 设计要点 |
|----|-------------|------------|----------|
| B1 | `retry` | verify→generate 重试 | 第一次 patch 故意错误；`fake_script` 两步 patch；`generate_max_attempts: 2` |
| B2 | `decoy` | Locate 找对文件 | `calc.py` + `calc_backup.py`；仅前者应被修改 |
| B3 | `gate_boundary` | Gate 不误入 fix_bug | 消息像 explain；期望 `route=open` 或 `intent_id≠fix_bug` |
| B4 | `no_rig` | 无 index.db 回退 | 工作区不跑 `rig build`；仅靠 search/files_hint |
| B5 | `multi_file` | 改 root cause 文件 | 已有 `import_chain_rate` 可升格为 B5 基准；加 `must_modify` |

**tier 建议**：B1/B2/B4 → `medium`；B3 → `easy`（Gate 专项）；B5 → `medium`。

### Done（P1）

- [ ] 5 条任务入库，`dimension` 字段文档化  
- [ ] 5 条均过 L2 契约测（FakeModel）  
- [ ] live 可选跑，报告按 `failure_type` 聚合（不要求 live 全过）

---

## 9. 踩坑库 + QA_LOG（P2 · 持续）

### 9.1 文件

```
tests/regression/test_discovered_bugs.py   # 每个 bug 一个 class
docs/eval/QA_LOG.md                        # 轮次记录模板
```

### 9.2 QA_LOG 条目模板

```markdown
## 轮次 N — {标题}

| 任务/触发 | failure_type | 根因文件:行 | 修复 | 回归测试 |
|-----------|--------------|-------------|------|----------|
| off_by_one live | generate_patch_match | generate.py | … | TestBug_PatchNormalize… |

### 出厂条件（本轮）
- [ ] L2 契约全绿
- [ ] 本轮新 bug 均有回归 class
```

### 9.3 与 live 联动

每次 live eval 新增失败且根因明确 → 追加 QA_LOG 一行 → 补 `test_discovered_bugs.py` → 能在 L1/L2 复现则**不必**依赖 Ollama。

### Done（P2）

- [x] `docs/eval/QA_LOG.md` 初始化（可写入 GL-5 / 波次 C 已知失败）  
- [x] ≥3 条历史已知问题沉淀为 regression class

---

## 10. Locate 质量门槛（P2 · harness 改动）

### 10.1 行为变更（可选 feature flag）

在 `run_locate` 末尾：

```python
if architecture_requires_snippet(ctx) and not any(has_source_lines(s) for s in snippets):
    return NodeResult(ok=False, message="locate：无有效源码 snippet", ...)
```

或通过 planner 模板 / 任务级 `architecture.locate.min_snippets_with_source_lines` 驱动。

**默认**：仅对含 `architecture.locate` 契约的任务启用，避免破坏现有 harness E2E。

### 10.2 Done（P2）

- [x] 契约任务 B4/no-hint 触发 fail 而非拖到 generate  
- [x] `test_harness_locate_snippets.py` / 契约测更新  
- [x] `phase5-graph.md` §7 黄金五步「Locate ≥1 snippet」与实现一致

---

## 11. 优先级与派活顺序

| 优先级 | 工作包 | 依赖 | 估时 |
|--------|--------|------|------|
| **P0-a** | §5 报告 `pipeline_ok` + `failure_type` + session | — | 小 |
| **P0-b** | §6 `architecture` schema + `test_eval_contract.py` | P0-a 可并行 | 中 |
| **P1-a** | §7 `test_slots_locate.py` | — | 中 |
| **P1-b** | §8 五条架构 bench | P0-b | 中 |
| **P2-a** | §9 QA_LOG + discovered_bugs | P0-b | 持续 |
| **P2-b** | §10 Locate 门槛 | P1-a、P1-b | 中 |

**建议严格顺序**：P0-a → P0-b → P1-a ∥ P1-b → P2-a 持续 → P2-b。

---

## 12. 与波次 C / CI 的关系

| 项目 | 波次 C | 波次 D（本计划） |
|------|--------|------------------|
| 终判 verify 对齐 | ✅ | 维持 |
| `grading` / `tier` | ✅ | 维持 |
| `--fake` CLI | 已移除 | 由 **L2 契约 pytest** 替代 |
| live 探针 | ✅ | 增强报告 |
| CI | 仅全量 pytest | + `test_eval_contract` + `tests/diagnostic/` |

不在本波次修复：EV-7 文档声称的 `harness-eval` job 与代码不一致——可在 P0 文档一并更正。

---

## 13. Done Definition（波次 D 结项）

- [x] P0：`pipeline_ok` / `failure_type` / observability 字段上线 + 测试  
- [x] P0：≥3 任务 `architecture` + `fake_script` + 契约测全绿  
- [x] P1：`test_slots_locate.py` 达到 D1–D3 门槛  
- [x] P1：5 条架构维度 bench 入库且契约全绿  
- [x] P2：`QA_LOG.md` + ≥3 条 discovered_bugs  
- [x] P2：Locate 门槛（至少契约任务启用）  
- [x] `eval/README.md` + 本 struct 状态更新为结项  
- [x] 全量 pytest + ruff 不低于派活前基线  
- [x] 无新增 pip 依赖  

---

## 14. 参考

- KWCode：`kaiwu/tests/diagnostic/` · `bench_tasks.json` · `QA_LOG.md` · `GapDetector`  
- 本仓库：[`eval-repair-plan.md`](./eval-repair-plan.md) · [`phase5-graph.md`](./phase5-graph.md) §7 · `mini_coding_agent/modes/graph/session_ctx.py`

---

## 15. 展开文档索引（波次 D 详细规格）

本 struct 为总纲；实施细节、用例 ID、任务 JSON 示例、Done checklist 见 [`docs/eval/`](../eval/README.md)：

| 文档 | 内容 |
|------|------|
| [`01-design-overview.md`](../eval/01-design-overview.md) | KWCode 对照 · 双层 eval 语义 |
| [`02-five-layer-system.md`](../eval/02-five-layer-system.md) | L1–L5 · CI 策略 |
| [`03-task-schema.md`](../eval/03-task-schema.md) | tasks.json · architecture · fake_script |
| [`04-failure-taxonomy.md`](../eval/04-failure-taxonomy.md) | failure_type · 推断顺序 |
| [`05-pipeline-checklist.md`](../eval/05-pipeline-checklist.md) | Phase 0–8 逐步验证（58 项） |
| [`06-l1-diagnostic-spec.md`](../eval/06-l1-diagnostic-spec.md) | G/SL/L/GN/V/R 用例与 D1–D3 门槛 |
| [`07-l2-contract-spec.md`](../eval/07-l2-contract-spec.md) | assert_pipeline_contract |
| [`08-l3-arch-bench-spec.md`](../eval/08-l3-arch-bench-spec.md) | B1–B5 完整任务设计 |
| [`09-l4-live-probe-spec.md`](../eval/09-l4-live-probe-spec.md) | TaskResult 扩展 · 报告格式 |
| [`QA_LOG.md`](../eval/QA_LOG.md) | 踩坑记录 · GL-5 轮次 0 |
| [`10-implementation-roadmap.md`](../eval/10-implementation-roadmap.md) | P0–P2 派活与验收 |

---

*eval-architecture-plan.md · 波次 D · 2026-06-05*
