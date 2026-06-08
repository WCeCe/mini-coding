# Phase 7 — fix_bug Generate 与 Harness 前置

> **状态**：进行中（7.1 ✅ · 7.2 ✅ · 7.3 ✅ · **7.4 ✅**）  
> **Live 产物**：[`eval/runs/README.md`](../../eval/runs/README.md)

Phase 7 聚焦 **fix_bug 路径 Generate 质量** 与 **eval 可观测性**，不改动 Gate / Planner 模板。

---

## 子阶段索引

| 子阶段 | 文档 | 内容 | 状态 |
|--------|------|------|------|
| **7.1** | [`phase7.1-generate-fix-bug.md`](./phase7.1-generate-fix-bug.md) | 写前禁止改 `tests/`；verify fail 回滚 checkpoint + test baseline | ✅ |
| **7.2** | [`phase7.2-guided-patch.md`](./phase7.2-guided-patch.md) | 系统注入 `old_text`，LLM 只产 `new_text`；RIG 前置；取消 open 降级；`stage_trace` | ✅ |
| **7.3** | [`phase7.3-outline.md`](./phase7.3-outline.md) | protocol 未闭合 JSON + 围栏；slots 函数调用 hint | ✅ |
| **7.4** | [`phase7.4-eval-grading.md`](./phase7.4-eval-grading.md) | 写盘尾随 `\n`；`nameerror_greet` → tests_only | ✅ |

---

## 基础设施变更（7.2 一并落地）

| 项 | 位置 | 说明 |
|----|------|------|
| 强制 RIG | `index/build.ensure_rig` + `pipeline.run_pipeline` | 临时 eval 工作区自动建 `rig.db` |
| 取消 pipeline→open | `runner.handle_ask` | 流水线失败直接返回错误，不降级 open |
| 阶段追踪 | `harness_trace.py` + `observability.stage_trace` | 每次 eval 记录各阶段 input/output |
| Live 产物目录 | `eval/runs/` | 根目录不再散落 `eval_live_*.json` |

---

## Live 结果摘要（Generate 专项 8 条）

| 指标 | phase71（7.1 后） | phase72（7.2 后） |
|------|-------------------|-------------------|
| passed（Generate 8） | 0/8 | **5/8** |
| passed（全量 19） | — | **8/19**（[`baselines/post72`](../../eval/baselines/README.md)） |
| 主 failure | fallback_open、old_text 0 匹配 | expect_files / protocol、no_file_hint |

详见 [`eval/runs/README.md`](../../eval/runs/README.md) § Phase 7 Generate 8 条汇总。

---

## 阅读顺序

1. 本文（总览）
2. [`phase7.1-generate-fix-bug.md`](./phase7.1-generate-fix-bug.md) — 策略与 retry 回滚
3. [`phase7.2-guided-patch.md`](./phase7.2-guided-patch.md) — 引导 patch 与 eval 基建
4. [`phase7.3-outline.md`](./phase7.3-outline.md) — protocol + locate
5. [`phase7.4-eval-grading.md`](./phase7.4-eval-grading.md) — 换行 + 任务改版
6. [`docs/eval/QA_LOG.md`](../eval/QA_LOG.md) — 踩坑与回归

---

*phase7.md · Generate 迭代总纲 · 2026-06-08*
