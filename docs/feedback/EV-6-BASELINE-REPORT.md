# EV-6-BASELINE-REPORT — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-6-BASELINE-REPORT
- **状态**: 完成

---

## 方案摘要

1. **`parse_harness_steps(stderr)`** — 从 `[gate]` / `[harness] … locate|generate|verify ok|fail` 解析结构化分步。
2. **`TaskResult.steps`** — 每任务附带分步数组；失败时追加 `post_check` / `exception`。
3. **CLI** — `--save-baseline PATH`、`--compare PATH`、`--report json`。
4. **`eval/baselines/README.md`** — 基线命名与对比工作流。

### 改动文件

| 路径 | 说明 |
|------|------|
| `eval/run_eval.py` | steps、baseline、compare、json 报告 |
| `eval/README.md` | 基线工作流、harness-eval vs agent-eval |
| `eval/baselines/README.md` | **新增** |
| `tests/test_eval_runner.py` | +5 条 |

---

## 验证结果

```
python -m pytest tests/test_eval_runner.py -q  →  35 passed
python -m ruff check eval/run_eval.py tests/test_eval_runner.py  →  All checks passed!
```

---

## 主 Agent 复审

- **结论**: **通过**
- **备注**: 2026-06-05 主 Agent 实现并复验。

---

*EV-6-BASELINE-REPORT · 2026-06-05*
