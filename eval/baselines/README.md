# Eval 基线目录

存放 `python eval/run_eval.py --save-baseline eval/baselines/<name>.json` 生成的 **live** 基线。

## 建议命名

| 文件 | 用途 |
|------|------|
| `live-qwen2.5-coder-7b.json` | 默认模型的 agent 能力基线 |

## 对比

```bash
python eval/run_eval.py --save-baseline eval/baselines/live-qwen2.5-coder-7b.json
python eval/run_eval.py --compare eval/baselines/live-qwen2.5-coder-7b.json
```

Eval **仅使用 Ollama 真实模型**，无 FakeModel 模式。
