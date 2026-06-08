# Eval 文档索引（波次 D）

> **状态**：✅ 规格与 repo 对齐（Batch 5–6）· L1 部分用例在 harness 测试中  
> **前置**：Phase 5 + 黄金闭环 ✅ · Eval 波次 C/D ✅  
> **struct 契约**：[`struct/eval-architecture-plan.md`](../struct/eval-architecture-plan.md)（波次 D 总纲）

本目录是 **Eval 波次 D** 的完整实施文档，目标是把 eval 从「结果探测器」升级为「**架构探测器 + 能力探针**」双层体系。对照 [KWCode](https://github.com/zou0613/kwcode) 的分层思路，贴合本仓库 **Gate → slots → Locate → Generate → Verify → retry** 的 fix_bug DAG。

---

## 阅读顺序

| 顺序 | 文档 | 内容 |
|------|------|------|
| 1 | [`01-design-overview.md`](./01-design-overview.md) | 设计总览、KWCode 对照、核心原则、与波次 C 的关系 |
| 2 | [`02-five-layer-system.md`](./02-five-layer-system.md) | L1–L5 五层 eval 体系：职责、CI 策略、入口命令 |
| 3 | [`03-task-schema.md`](./03-task-schema.md) | `tasks.json` 完整字段、`architecture` / `fake_script` 契约 |
| 4 | [`04-failure-taxonomy.md`](./04-failure-taxonomy.md) | `failure_type` 枚举、推断顺序、与 `failure_step` 映射 |
| 5 | [`05-pipeline-checklist.md`](./05-pipeline-checklist.md) | Phase 0–8 逐步验证清单（架构每一步） |
| 6 | [`06-l1-diagnostic-spec.md`](./06-l1-diagnostic-spec.md) | L1 组件诊断：用例 ID、输入、期望、量化门槛 |
| 7 | [`07-l2-contract-spec.md`](./07-l2-contract-spec.md) | L2 契约 eval：`assert_pipeline_contract` 规范与测试入口 |
| 8 | [`08-l3-arch-bench-spec.md`](./08-l3-arch-bench-spec.md) | L3 五条架构维度 bench（B1–B5）完整任务设计 |
| 9 | [`09-l4-live-probe-spec.md`](./09-l4-live-probe-spec.md) | L4 Live 探针：报告字段、聚合、基线对比 |
| 10 | [`QA_LOG.md`](./QA_LOG.md) | 踩坑记录模板 + GL-5 / 波次 C 已知问题 |
| 11 | [`10-implementation-roadmap.md`](./10-implementation-roadmap.md) | P0 / P1 / P2 实施路线图、Done Definition、文件清单 |

---

## 快速定位

| 我想… | 去看 |
|--------|------|
| 理解为什么要做波次 D | [`01-design-overview.md`](./01-design-overview.md) §1–2 |
| 跑 CI 该执行哪些 pytest | [`02-five-layer-system.md`](./02-five-layer-system.md) §CI |
| 给 tasks.json 加 architecture 字段 | [`03-task-schema.md`](./03-task-schema.md) |
| 读 live 报告里的 failure_type | [`04-failure-taxonomy.md`](./04-failure-taxonomy.md) |
| 确认某一步有没有 eval 覆盖 | [`05-pipeline-checklist.md`](./05-pipeline-checklist.md) |
| 写 L1 诊断测试 | [`06-l1-diagnostic-spec.md`](./06-l1-diagnostic-spec.md) |
| 写 L2 契约测试 | [`07-l2-contract-spec.md`](./07-l2-contract-spec.md) |
| 新增架构 bench 任务 | [`08-l3-arch-bench-spec.md`](./08-l3-arch-bench-spec.md) |
| 扩展 run_eval.py 报告 | [`09-l4-live-probe-spec.md`](./09-l4-live-probe-spec.md) |
| 记录新踩坑 | [`QA_LOG.md`](./QA_LOG.md) |
| 派活 / 验收 | [`10-implementation-roadmap.md`](./10-implementation-roadmap.md) |

---

## 与现有文档的关系

| 文档 | 关系 |
|------|------|
| [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) | 波次 C 结项契约；本目录**继承** grading / verify 对齐，不重复 |
| [`struct/eval-architecture-plan.md`](../struct/eval-architecture-plan.md) | 波次 D struct 总纲；本目录是其**展开版** |
| [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7 | 黄金五步与 eval 工作流 |
| [`eval/README.md`](../../eval/README.md) | 操作手册（命令、环境）；本目录是**设计规格** |
| [`eval/runs/README.md`](../../eval/runs/README.md) | Live 跑分产物归档与 Phase 7 结果表 |
| [`eval/baselines/README.md`](../../eval/baselines/README.md) | 基线命名与对比用法 |
| [`eval/L4-ONLY-DECISION.md`](../../eval/L4-ONLY-DECISION.md) | L2 契约 7 条 + L4-only 12 条（Batch 5） |
| [`struct/phase7.md`](../struct/phase7.md) | Phase 7 Generate 迭代总纲 |
| [`struct/phase7.3-outline.md`](../struct/phase7.3-outline.md) | 7.3 大纲 |

---

## 产品决策（已对齐，全员遵守）

1. **不替换** `eval/run_eval.py` 主框架，在其上扩展报告与 schema。
2. **不引入**新 pip 依赖。
3. **接受** live 短期仍可能低分——报告必须能回答「该改哪个节点」。
4. **分拆** CI 必跑的架构回归（L1–L3，零 LLM）vs 手动的 live 能力探针（L4）。
5. **tasks.json 是单一真相源**：L2 契约测直接读任务清单，不再与 harness 测试脱节。

---

*docs/eval · Batch 5–6 对齐 · 2026-06-08*
