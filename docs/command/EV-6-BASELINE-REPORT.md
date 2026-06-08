# EV-6-BASELINE-REPORT — 结构化报告与基线对比

## 元信息

- **TASK_ID**: EV-6-BASELINE-REPORT
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P1
- **可以写代码**: 是
- **依赖**: EV-1、EV-2、EV-3（至少 EV-1+EV-2）

---

## 目标

增强 `eval/run_eval.py`：输出 **结构化分步结果**（gate/locate/generate/verify/post_check）；支持 `--save-baseline PATH` 与 `--compare PATH`，用于回归对比。可选 JSON 报告格式。

---

## 约束

- 不新增 pip 依赖；基线文件为 JSON（标准库）
- `TaskResult` 扩展字段须有测试
- Markdown 报告保持向后兼容（默认行为不变）
- 铁律 §8：CLI help 中文

---

## 交付物

- `eval/run_eval.py` — baseline / compare / 可选 `--report json`
- `eval/baselines/.gitkeep` 或 README 说明目录用途
- `tests/test_eval_runner.py`
- `eval/README.md` 基线工作流一节
- 回报：[`feedback/EV-6-BASELINE-REPORT.md`](../feedback/EV-6-BASELINE-REPORT.md)

---

## 验收标准

- [ ] `--save-baseline` 写入可解析 JSON（含每 task pass/fail/failure_step/elapsed_ms）
- [ ] `--compare` 输出新增 fail / 恢复 pass 摘要
- [ ] 失败任务报告含分步字段（非仅 stderr 猜测）
- [ ] pytest + ruff 通过

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §6
