# EV-7-DOCS-CI — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-7-DOCS-CI
- **状态**: 完成

---

## 方案摘要

### harness-eval vs agent-eval

| 指标 | 命令 | CI | 含义 |
|------|------|-----|------|
| **harness-eval** | `--fake` | ✅ 独立 job | 管线回归；15/15 ≠ agent 聪明 |
| **agent-eval** | `--live` | ❌ 不纳入 CI | 真实 Ollama；作品集手动归档 |

### 改动文件

| 路径 | 说明 |
|------|------|
| `eval/README.md` | 对照表（EV-6 已写） |
| `.github/workflows/ci.yml` | 新增 `harness-eval` job（ubuntu · `--fake`） |
| `docs/struct/eval-repair-plan.md` | 状态更新 |
| `docs/command/EVAL-REPAIR-OVERVIEW.md` | 任务状态 |
| `docs/feedback/EV-7-DOCS-CI.md` | 本回报 |

### Live 基线（冻结）

| 环境 | 模型 | easy 5 条 | 全量 15 条 |
|------|------|-----------|------------|
| Windows | `qwen2.5-coder:7b` | **2/5**（GL-5） | 未全量跑；medium 预期 0/3 |

---

## 主 Agent 复审

- **结论**: **通过**

---

*EV-7-DOCS-CI · 2026-06-05*
