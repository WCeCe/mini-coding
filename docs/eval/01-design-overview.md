# Eval 设计总览（波次 D）

> 返回索引：[`README.md`](./README.md)

---

## 1. 问题陈述

波次 C（EV-1–7）结项后，`eval/` 已具备：

- `grading` / `tier` / `lock_tests` 评分 schema
- harness `verify` 与 eval 终判语义对齐（EV-1）
- Generate / protocol 鲁棒性加固（EV-3）
- 15 条任务（easy 12 + medium 3）
- 结构化分步报告 + 基线对比（EV-6）

但仍存在**架构评测缺口**——eval 能测「结果对不对」，不能系统性地测「harness 哪一环是架构痛点」：

| 发现 | 严重度 | 说明 |
|------|--------|------|
| eval 终判只看磁盘 + pytest，**不读 session** | P0 | `last_gate` / `last_verify` / `harness_last_node` 已有，报告未用 |
| **无 `pipeline_ok` 与 `outcome_ok` 分拆** | P0 | open 降级或终判碰巧通过时，无法区分「管线成功 vs 仅结果对」 |
| 失败归因靠 stderr 正则，**无稳定 taxonomy** | P0 | 难做 E2E 分因与跨版本对比 |
| `tasks.json` 与 FakeModel 管线回归**脱节** | P0 | `test_harness_*` 手写场景，不读任务清单 |
| Locate **永远 ok=True** | P1 | 无 snippet 质量门槛 |
| 任务集按**数量**扩展，未按**架构维度**覆盖 | P1 | 缺 retry / decoy / gate 边界 / 无 RIG 等专项 |
| 无踩坑固化流程 | P2 | 无 `test_discovered_bugs` / QA_LOG 循环 |

**波次 D 目标**：把 eval 从「结果探测器」升级为「**架构探测器 + 能力探针**」双层体系。

---

## 2. KWCode Eval 设计对照

本仓库不嵌入 KWCode，但借鉴其 **Eval 驱动架构迭代** 的分层思路。KWCode v1.6.0 → v2.0.0 的演进（bench 0% → 20%，+83 tests）体现了「先建诊断体系，再改架构」的路径。

### 2.1 KWCode 五层 eval（映射到本仓库）

```
KWCode                          本仓库（波次 D）
─────────────────────────────────────────────────────
L1  kaiwu/tests/diagnostic/     tests/diagnostic/
    63 专项诊断，零 LLM          Gate/slots/locate/protocol/verify 组件测

L2  bench_tasks + FakeModel     tasks.json architecture + fake_script
    管线契约断言                 tests/test_eval_contract.py

L3  架构维度 bench               dimension: retry/decoy/gate/no_rig/multi_file
    retry/decoy/gate/…           eval/tasks.json 扩展 B1–B5

L4  live 能力探针               eval/run_eval.py + Ollama
    bench_diagnose.py            failure_type 聚合 + observability

L5  QA_LOG + discovered_bugs    docs/eval/QA_LOG.md
    踩坑固化循环                 tests/regression/test_discovered_bugs.py
```

### 2.2 KWCode 三大痛点发现机制

#### A. GapDetector（零 LLM 规则归因）

KWCode v1.6.0 定义 11 种 `GapType`，在 pipeline 执行过程中纯规则检测架构缺口，不依赖终判。

本仓库对应：**精简版 `failure_type` taxonomy**（14 类型），见 [`04-failure-taxonomy.md`](./04-failure-taxonomy.md)。不引入完整 GapDetector 模块，但在 `infer_failure_type()` 中实现同等归因能力。

#### B. bench_diagnose + attribute_failures_to_files

KWCode v2.0.0 的 `bench_diagnose.py` 把 stderr/轨迹转成可聚合诊断；v1.9.0 的 `attribute_failures_to_files` 精确到「应改 rates.py 却改了 app.py」。

本仓库对应：

- `architecture.must_modify` / `must_include_files` 契约字段
- `observability.files_touched` 报告字段
- `failure_type=locate_wrong_file` 等精确归因

#### C. QA_LOG 踩坑闭环

```
live eval 新失败 → QA_LOG 记录 → test_discovered_bugs.py → L1/L2 复现 → 下轮不再复发
```

见 [`QA_LOG.md`](./QA_LOG.md)。

### 2.3 本仓库与 KWCode 的关键差异

| 维度 | KWCode | mini-coding-agent |
|------|--------|-------------------|
| 定位 | BM25 + AST 调用图（零 LLM） | RIG index + search 回退 |
| Gate | 确定性优先 + LLM 兜底 | 纯 LLM 分类 |
| Debug | sys.settrace 运行时调试 | verify 错误摘要 → generate retry |
| 降级 | 无 open loop | pipeline fail → `agent.ask()` |
| Eval 现状 | 完整五层 + GapDetector | 波次 C 完成；波次 D 文档 + 待实现 |

**本仓库独有 eval 需求**：必须区分 `pipeline_ok`（管线按设计执行）与 `outcome_ok`（磁盘终判通过），因为 **open fallback** 可能碰巧修好 bug。

---

## 3. 架构全流程（fix_bug 黄金路径）

```
用户 message
  → handle_ask(harness_enabled=True)
    → Gate（1× LLM：intent + confidence + route）
      → session.last_gate
    → [route≠harness_pipeline] → open: agent.ask()  ← S9
    → load_skill（可选）
    → Planner：fix_bug.json + fill_slots（规则，无 LLM）
    → Executor 拓扑执行：
        locate（RIG/search/read_file，无 LLM）
        → generate（1× LLM → patch/write，governance）
        → verify（lock_tests → pytest/py_compile）
        → [verify fail, retry≤2] → generate  ← S6–S7
    → session.last_verify / last_files_touched
    → [pipeline fail] → open 降级  ← S9
  → eval 终判：check_task_grading（lock → exact → verify）
```

完整逐步验证矩阵见 [`05-pipeline-checklist.md`](./05-pipeline-checklist.md)。

---

## 4. 双层 eval 语义

| 维度 | 字段 | 定义 | 典型用途 |
|------|------|------|----------|
| **结果** | `outcome_ok` | `check_task_grading()` 通过 | 「bug 修好了吗？」 |
| **管线** | `pipeline_ok` | Gate 契约 + 无 open 降级 + `architecture` 断言全过 | 「harness 按设计跑了吗？」 |
| **Live 默认** | `passed` | `outcome_ok` 且非 `fallback_open` | 能力探针主指标 |
| **严格模式** | `passed`（`--strict-pipeline`） | 上述 + `pipeline_ok` | 架构回归 |

### 4.1 为什么要分拆

| 场景 | outcome_ok | pipeline_ok | 结论 |
|------|------------|-------------|------|
| harness 全链路成功，pytest 通过 | ✅ | ✅ | 理想状态 |
| locate 找错文件，open 碰巧修对 | ✅ | ❌ | **架构问题**，不应算 harness 成功 |
| generate patch 错，retry 后 verify 仍 fail，open 修对 | ✅ | ❌ | 同上 |
| harness verify 通过但 grading exact 不符 | ❌ | ✅ | **模型/生成问题**，管线本身 OK |
| Gate confidence=low，直接 open 修对 | ✅ | ❌ | Gate 需改进 |

---

## 5. 五层 eval 体系摘要

详见 [`02-five-layer-system.md`](./02-five-layer-system.md)。

| 层 | 回答的问题 | CI | LLM |
|----|------------|-----|-----|
| L1 组件诊断 | 每个**节点本身**有没有 bug？ | ✅ 必绿 | ❌ |
| L2 契约 eval | 任务设计的**管线契约**是否执行？ | ✅ 必绿 | ❌ FakeModel |
| L3 架构 bench | **架构维度**是否覆盖？ | ✅ 建议 | ❌ FakeModel |
| L4 Live 探针 | 真实模型下 harness **够不够用**？ | ❌ 手动 | ✅ Ollama |
| L5 踩坑固化 | 漏洞是否**不再复发**？ | ✅ 随增长 | ❌ |

---

## 6. 与波次 C 的继承关系

| 波次 C 交付 | 波次 D 态度 |
|-------------|-------------|
| verify 与 eval 终判对齐 | **维持**，L2/L4 共用 `verify_rules.py` |
| `grading` / `tier` / `lock_tests` | **维持**，终判逻辑不变 |
| `--fake` CLI（已移除） | 由 **L2 契约 pytest** 替代 |
| live 探针 + 基线对比 | **增强**报告字段 |
| 15 条任务 | **扩展** architecture + dimension |

波次 C 诚实基线（冻结对比点）：

| 环境 | 模型 | 结果 | 日期 |
|------|------|------|------|
| Windows | `qwen2.5-coder:7b` | **2/5**（原 5 条 easy） | GL-5 / 2026-06-05 |

波次 D 结束后须更新此表；**禁止**仅报告 L2 契约通过率冒充 live 能力。

---

## 7. 设计原则

1. **诚实指标优先于刷分**：live 2/15 可接受，报告必须说清 failure_type 分布。
2. **CI 不依赖 LLM**：L1–L3 全 FakeModel，稳定绿；L4 手动 / nightly。
3. **tasks.json 是单一真相源**：L2 契约测 parametrized 读 `fake_script` 任务，不与 harness 测试脱节。
4. **每个 failure_type 对应一个改动点**：报告尾部给出「建议优先改动」排序。
5. **踩坑必须固化**：live 新失败 → QA_LOG → regression test → 下轮不再复发。
6. **最小 diff 实现**：扩展 `TaskResult` / `tasks.json`，不重写 eval 框架。
7. **不新增 pip 依赖**。

---

## 8. 预期 eval 报告能回答的三个问题

**Q1：架构哪一环是瓶颈？**

```
failure_type 聚合：generate_patch_match × 5, locate_wrong_file × 2
→ 优先改 mini_coding_agent/modes/graph/nodes/generate.py
```

**Q2：某条任务是管线问题还是模型问题？**

```
import_chain_rate: pipeline_ok=False (改了 app.py 而非 rates.py)
                 outcome_ok=False
→ 架构问题（locate），不是模型能力问题
```

**Q3：这次改动有没有引入回归？**

```
--compare 基线：新增失败 0，恢复通过 2，仍失败 3
→ 改动安全，继续迭代 generate
```

---

*01-design-overview.md · 波次 D · 2026-06-05*
