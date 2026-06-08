# 黄金闭环 Eval

通过 **Ollama 真实模型** 度量 `fix_bug` 路径：`handle_ask(..., harness_enabled=True)` + 隔离临时仓库 + 文件/verify 断言。

**设计规格（波次 D）**：[`docs/eval/README.md`](../docs/eval/README.md) — 五层体系、task schema、failure_type、逐步验证清单、实施路线图。

契约见 [`docs/struct/phase5-graph.md`](../docs/struct/phase5-graph.md) §7。

## 前置

| 要求 |
|------|
| Python 3.10+，与主仓库相同依赖 |
| 本机 `ollama serve` 已启动 |
| 已 `ollama pull` 目标模型（默认 `qwen2.5-coder:7b`） |

## 用法

在仓库根目录执行：

```bash
# 全量 eval（须 Ollama）
python eval/run_eval.py

# 仅跑一条任务
python eval/run_eval.py --task nameerror_calc

# CSV / JSON 报告
python eval/run_eval.py --report csv
python eval/run_eval.py --report json

# 调大超时 / token（慢模型或复杂 patch）
python eval/run_eval.py --ollama-timeout 180 --max-new-tokens 768

# 保存基线 + 对比回归
python eval/run_eval.py --save-baseline eval/baselines/live-qwen2.5-coder-7b.json
python eval/run_eval.py --compare eval/baselines/live-qwen2.5-coder-7b.json
```

退出码：`0` 全部 pass；`1` 存在 fail；`2` Ollama 预检失败。

框架单测（不跑 Ollama，仅 schema / grading / 基线逻辑）：

```bash
python -m pytest tests/test_eval_runner.py -q
```

可选集成测（本机有 Ollama 时）：

```bash
python -m pytest tests/test_eval_runner.py -m integration -q
```

## 与 CLI 的关系

交互式调试可用主 CLI（须显式开 harness）：

```bash
python -m mini_coding_agent.cli --harness on --approval auto
```

Eval 脚本**不**走 CLI，直接 `handle_ask(agent, message, harness_enabled=True)`。

## Agent 约定

- `approval_policy=auto`
- `enable_trace_hook=False`
- 每任务独立 `tempfile` 目录
- 使用 `OllamaModelClient`（与 CLI 默认 model/host 可对齐）

## tasks.json

当前 **19 条**（easy/medium 15 + 架构 bench 4）。基础字段见 [`docs/struct/eval-repair-plan.md`](../docs/struct/eval-repair-plan.md) §3。

波次 D 扩展字段 `architecture` / `fake_script` / `dimension` 见 [`docs/eval/03-task-schema.md`](../docs/eval/03-task-schema.md)（契约 7 条含 B1–B5 升格）。

## CI 与 harness 测试

| 层 | 命令 | LLM |
|----|------|-----|
| L1 组件诊断 | `pytest tests/diagnostic/ -q` | ❌ |
| 踩坑回归 | `pytest tests/regression/ -q` | ❌ FakeModel |
| L2 契约 eval | `pytest tests/test_eval_contract.py -q` | ❌ FakeModel |
| Harness 回归 | `pytest tests/test_harness_*.py -q` | ❌ FakeModel |
| L4 Live 探针 | `python eval/run_eval.py` | ✅ Ollama |

完整五层说明：[`docs/eval/02-five-layer-system.md`](../docs/eval/02-five-layer-system.md)。

## 两层 eval 指标（波次 D）

| 指标 | 含义 | 状态 |
|------|------|------|
| `outcome_ok` | grading 终判通过（bug 修好了吗） | ✅ |
| `pipeline_ok` | Gate 契约 + 无 open 降级 + architecture 断言 | ✅（有 `architecture` 的任务） |
| `failure_type` | 稳定失败分类（如 `generate_patch_match`） | ✅ |
| `observability` | session：`last_gate` / `last_verify` / `files_touched` 等 | ✅ |

`--strict-pipeline`：除 `outcome_ok` 外还要求 `pipeline_ok == True`。

详见 [`docs/eval/09-l4-live-probe-spec.md`](../docs/eval/09-l4-live-probe-spec.md)。

## 报告

Markdown 默认输出到 stdout。失败任务附 **结构化分步**（gate → locate → generate → verify → post_check）。

### 读失败步（当前）

| 模式 | failure_step |
|------|--------------|
| `confidence=low` / `route=open` | Gate |
| `locate fail` | Locate |
| `generate 须返回 tool` | Generate |
| `verify fail` | Verify |
| `内容与期望不符` | expect_files |
| `pytest 失败` | verify |

### 读 failure_type

JSON/Markdown 报告含 `failure_type` 字段；失败任务尾部有 **架构痛点聚合** 表与 **建议优先改动** 列表。

| failure_type | 建议改动 |
|--------------|----------|
| `generate_patch_match` | `nodes/generate.py` |
| `generate_protocol` | `protocol.py` |
| `locate_wrong_file` | `nodes/locate.py` |
| `gate_low` | `gate.py` |
| `fallback_open` | `runner.py` + 上游 |

双指标：`outcome_ok`（终判）与 `pipeline_ok`（契约，仅含 `architecture` 的任务）。默认 `passed == outcome_ok`；`--strict-pipeline` 时两者皆须通过。

完整枚举：[`docs/eval/04-failure-taxonomy.md`](../docs/eval/04-failure-taxonomy.md)。

## Live 工作流

1. `ollama serve` + `ollama pull qwen2.5-coder:7b`
2. `python eval/run_eval.py --task nameerror_calc` 单条试跑
3. 全量跑并 `--save-baseline`
4. 改代码后 `--compare` 看回归
5. 失败看报告 **分步结果**，只改对应节点

**说明**：Harness 单元测试（`tests/test_harness_*.py`）仍用 `FakeModelClient` 测管线接线；**eval 只测真实 agent 能力**。

不新增 pip 依赖；仅标准库 + 现有 `mini_coding_agent`。
