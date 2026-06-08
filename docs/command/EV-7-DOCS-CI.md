# EV-7-DOCS-CI — 文档诚实化与 CI 分层

## 元信息

- **TASK_ID**: EV-7-DOCS-CI
- **TASK_TYPE**: DOCS
- **优先级**: P2
- **可以写代码**: 是（限 CI 可选 step）
- **依赖**: EV-4、EV-5、EV-6

---

## 目标

更新项目文档，**明确区分**：

| 指标 | 含义 |
|------|------|
| **harness-eval**（`--fake`） | 管线回归；5/5 ≠ agent 聪明 |
| **agent-eval**（`--live`） | 真实模型能力；作品集引用此项 |

同步 `struct/`、`eval/README.md`、根 `README.md` eval 小节；CI 可选增加独立 `python eval/run_eval.py --fake` step（不替代 pytest）。

---

## 约束

- 不夸大 live 通过率；保留 GL-5 与 2026-06-05 基线表
- CI 变更不得破坏现有 matrix（pip/uv × os）
- 铁律 §8

---

## 交付物

- `eval/README.md`、`docs/struct/eval-repair-plan.md`（状态板）、`docs/struct/phase5-graph.md` §9 交叉引用
- 根 `README.md` eval 段落（若有）
- 可选：`.github/workflows/ci.yml` 注释或 eval step
- 回报：[`feedback/EV-7-DOCS-CI.md`](../feedback/EV-7-DOCS-CI.md)

---

## 验收标准

- [ ] 文档含 harness-eval vs agent-eval 对照表
- [ ] live 基线 2/5 可见且标注环境
- [ ] CI 仍全绿（若改 workflow）
- [ ] 主 Agent 可据此写 EV-REVIEW

---

## 参考资料

- [`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md)
- [`EVAL-REPAIR-OVERVIEW.md`](./EVAL-REPAIR-OVERVIEW.md)
