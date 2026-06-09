# Eval 基线目录

存放 **长期对比** 用的 live 基线（`--save-baseline`）。**单次跑分报告** 放 [`../runs/`](../runs/README.md)。

## 正式基线（Phase 7.2 后）

| 文件 | 模型 | 任务 | 说明 |
|------|------|------|------|
| **`live-qwen2.5-coder-7b-post82.json`** | qwen2.5-coder:7b | 全量 **19** | **当前正式基线**（Phase 8.2 P1：**18/19**，2026-06-09） |
| `live-qwen2.5-coder-7b-post74-rerun.json` | 同上 | 全量 19 | Phase 8.1 后重跑（**11/19**） |
| `live-qwen2.5-coder-7b-post72.json` | 同上 | 全量 19 | Phase 7.2 批次（11/19） |

历史参考（**非**正式对比基线）：

| 文件 | 说明 |
|------|------|
| `live-qwen2.5-coder-7b.json` | 若存在：7.2 前旧命名；请改用 `-post72` |

对应 live 报告：`eval/runs/live/2026-06-08_post-72-full-19tasks.json`（与基线同次 `--save-baseline` 产出）。

## 指标口径（与 runs/README 一致）

| 指标 | 含义 |
|------|------|
| **19 条全量** | `passed/total` in baseline `summary` |
| **Generate 专项 8 条** | 子集汇总见下文 §Phase 7（**5/8** @ 7.2 批次） |
| **全量 19 条（post-8.2）** | **18/19** · `live-qwen2.5-coder-7b-post82.json`（2026-06-09，P1） |
| **全量 19 条（post-7.2）** | **11/19** · `live-qwen2.5-coder-7b-post74-rerun.json`（2026-06-08） |
| **L2 契约** | 7 条；见 [`L4-ONLY-DECISION.md`](../L4-ONLY-DECISION.md) |

`fallback_open` 在 7.2 后应为 **0**；若基线中出现该 failure_type，说明跑分时代码或任务环境非 7.2+。

## 对比

```bash
# 跑全量并更新基线
python eval/run_eval.py --report json \
  -o eval/runs/live/$(date +%F)_full-19tasks.json \
  --save-baseline eval/baselines/live-qwen2.5-coder-7b-post82.json

# 改代码后对比
python eval/run_eval.py --compare eval/baselines/live-qwen2.5-coder-7b-post82.json
```

Eval **仅使用 Ollama 真实模型**，无 FakeModel 模式。
