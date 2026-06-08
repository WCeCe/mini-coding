# Live Eval 运行产物

本目录存放 **L4 live 探针** 的 JSON / Markdown 报告与实验记录。**不要**在仓库根目录散落 `eval_live_*.json`。

## 目录结构

| 子目录 | 用途 |
|--------|------|
| [`live/`](./live/) | 正式批次跑分（按日期 + 任务集命名） |
| [`experiments/`](./experiments/) | 单任务对比、RIG 实验、阶段追踪调试 |
| [`stderr/`](./stderr/) | 对应批次的 harness stderr（可选） |

**基线对比**（长期跟踪）仍用 [`../baselines/`](../baselines/) + `--save-baseline` / `--compare`。

## 命名约定

```
YYYY-MM-DD_{批次说明}.{json|md}
```

示例：`2026-06-08_phase72-generate-7tasks.json`

## 已归档运行（Phase 7 Generate 专项）

| 文件 | 模型 | 任务集 | passed | 说明 |
|------|------|--------|--------|------|
| [`live/2026-06-08_post-72-full-19tasks.json`](./live/2026-06-08_post-72-full-19tasks.json) | qwen2.5-coder:7b | 全量 19 | **8/19** | Phase 7.2 后正式批次（无 fallback_open） |
| [`live/2026-06-08_full-19tasks.json`](./live/2026-06-08_full-19tasks.json) | qwen2.5-coder:7b | 全量 19 | 7/19 | Phase 7 改前（含 fallback_open） |
| [`live/2026-06-08_phase71-generate-8tasks.json`](./live/2026-06-08_phase71-generate-8tasks.json) | 同上 | Generate 专项 8 | 0/8 | 7.1 后仍失败（old_text / open） |
| [`live/2026-06-08_phase72-generate-7tasks.json`](./live/2026-06-08_phase72-generate-7tasks.json) | 同上 | 7.1 批次减 off_by_one | **4/7** | 7.2 引导 patch 后 |
| [`live/2026-06-08_phase72-off_by_one_sum-pass.json`](./live/2026-06-08_phase72-off_by_one_sum-pass.json) | 同上 | 单条 off_by_one_sum | **1/1** | 7.2 验证 |

含 `stage_trace` 的 Markdown 摘要见同名的 `.md` 文件。

### 实验记录

| 文件 | 说明 |
|------|------|
| [`experiments/2026-06-08_off_by_one_rig-compare.json`](./experiments/2026-06-08_off_by_one_rig-compare.json) | RIG 有无对照 |
| [`experiments/2026-06-08_off_by_one_trace.json`](./experiments/2026-06-08_off_by_one_trace.json) | 首版阶段追踪（7.2 前） |

## 如何跑并写入本目录

```bash
# 单任务 + JSON 报告
python eval/run_eval.py --task off_by_one_sum --report json \
  -o eval/runs/live/$(date +%F)_off_by_one_sum.json

# Phase71 Generate 专项 7 条（不含 off_by_one_sum）
python eval/run_phase72_batch.py

# 全量 + 基线
python eval/run_eval.py --report json \
  -o eval/runs/live/$(date +%F)_full-19tasks.json \
  --save-baseline eval/baselines/live-qwen2.5-coder-7b-post72.json
```

报告字段说明：[`docs/eval/09-l4-live-probe-spec.md`](../../docs/eval/09-l4-live-probe-spec.md) · `observability.stage_trace` 记录 gate / rig / slots / locate / generate / verify 的 input/output。

## Phase 7 Generate 8 条汇总

| task_id | phase71 | phase72（7.2） |
|---------|---------|----------------|
| off_by_one_sum | fail | **pass**（单独复跑） |
| missing_return_abs | fail | **pass** |
| bench_retry_off_by_one | fail | **pass** |
| import_chain_rate | fail | **pass**（tests_only） |
| logic_median_even | fail | **pass** |
| syntaxerror_paren | fail | fail（protocol：` ```json ` 围栏） |
| nameerror_greet | fail | fail（protocol / expect_files） |
| no_file_hint_add | fail | fail（locate 无源码 hint） |

**合计：5/8**（phase72 批次 4/7 + off_by_one 单独 1）

设计说明：[`docs/struct/phase7.md`](../../docs/struct/phase7.md)
