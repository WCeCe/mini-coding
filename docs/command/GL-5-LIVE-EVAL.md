# GL-5-LIVE-EVAL — 真实 Ollama Eval 基线

## 元信息

- **TASK_ID**: GL-5-LIVE-EVAL
- **TASK_TYPE**: IMPLEMENT + DOCS
- **优先级**: P0
- **可以写代码**: 是（eval 与文档为主；不要求一次修通所有 live 任务）
- **依赖**: GL-1、GL-2、GL-3、GL-4 **全部** feedback 验收通过

---

## 目标

扩展 eval 至 3–5 个最小 `fix_bug` 任务；文档化 `--live` 真实 Ollama 跑法；**诚实记录**首次通过率与各 task 失败步骤，形成可复现基线。

---

## 约束

- 契约见 [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7.2 GL-5、§7
- CI 默认仍 FakeModel；`--live` 不强制进 GitHub Actions（除非用户另批）
- 失败 **允许**；feedback 必须写清失败在 Gate/Locate/Generate/Verify 哪一步
- 不为此任务去改 Hook / Skill / Gate 规则 / 非 fix_bug 意图
- 铁律 §8；eval 报告中文

---

## 交付物

- `eval/tasks.json` — 3–5 个任务（NameError、SyntaxError 等）
- `eval/run_eval.py` — `--live` 使用 `OllamaModelClient`
- `eval/README.md` — 环境、命令、读 `[harness]` stderr 定位表
- 回报：[`feedback/GL-5-LIVE-EVAL.md`](../feedback/GL-5-LIVE-EVAL.md)（**须含真实跑结果**，可部分 fail）

---

## 验收标准

- [ ] README 足够让他人按步骤复现 `--live`
- [ ] 至少 **1/5**（或 1/N）真实 task pass；其余 fail 有逐步定位
- [ ] FakeModel 模式 tasks 仍全 pass
- [ ] ruff + 全量 pytest 通过

---

## 参考资料

- [`struct/phase5-graph.md`](../struct/phase5-graph.md) §7
- [`models.py`](../../mini_coding_agent/models.py)
- [`cli.py`](../../mini_coding_agent/cli.py) — `--harness on` 用法可写入 README
