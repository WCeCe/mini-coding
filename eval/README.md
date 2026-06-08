# 黄金闭环 Eval

通过 **Ollama 真实模型** 度量 `fix_bug` 路径：`handle_ask(..., harness_enabled=True)` + 隔离临时仓库 + 文件/verify 断言。

| 文档 | 用途 |
|------|------|
| [`docs/eval/README.md`](../docs/eval/README.md) | 波次 D 设计规格（五层、schema、taxonomy） |
| [`docs/struct/phase7.md`](../docs/struct/phase7.md) | **当前主线**：Generate 7.1/7.2 |
| [`runs/README.md`](./runs/README.md) | **Live 跑分产物**（JSON/MD，按日期归档） |
| [`baselines/README.md`](./baselines/README.md) | 长期基线 `--save-baseline` / `--compare` |

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

# CSV / JSON 报告（建议写入 eval/runs/live/）
python eval/run_eval.py --report json -o eval/runs/live/2026-06-08_full-19tasks.json

# Generate 专项 7 条（phase72 批次脚本）
python eval/run_phase72_batch.py

# 调大超时 / token（慢模型或复杂 patch）
python eval/run_eval.py --ollama-timeout 180 --max-new-tokens 768

# 保存基线 + 对比回归
python eval/run_eval.py --save-baseline eval/baselines/live-qwen2.5-coder-7b-post72.json
python eval/run_eval.py --compare eval/baselines/live-qwen2.5-coder-7b-post72.json
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

波次 D 扩展字段 `architecture` / `fake_script` / `dimension` 见 [`docs/eval/03-task-schema.md`](../docs/eval/03-task-schema.md)。

**L2 契约 7 条 vs L4-only 12 条**：见 [`L4-ONLY-DECISION.md`](./L4-ONLY-DECISION.md)（Batch 5 决策，暂不扩 schema）。

## CI 与 harness 测试（L1–L5 命令总表）

| 层 | 回答什么 | 命令 | LLM | CI |
|----|----------|------|-----|-----|
| **L1** | 组件 I/O（slots/locate） | `python -m pytest tests/diagnostic/ -q` | ❌ | ✅ 必绿 |
| **L2** | 管线契约（7 条 fake_script） | `python -m pytest tests/test_eval_contract.py -q` | ❌ FakeModel | ✅ 必绿 |
| **L3** | 架构维度 B1–B5 | 同上（含 `dimension` 任务） | ❌ FakeModel | ✅ 必绿 |
| **L4** | 真模型能力（19 条） | `python eval/run_eval.py` | ✅ Ollama | ❌ 手动 |
| **L5** | 踩坑不复现 | `python -m pytest tests/regression/ -q` | ❌ FakeModel | ✅ 必绿 |

**补充（非独立层，CI 必绿）**：

| 套件 | 命令 |
|------|------|
| eval 框架 / grading | `python -m pytest tests/test_eval_runner.py -q` |
| Harness 回归 | `python -m pytest tests/test_harness_*.py tests/test_generate_robust.py -q` |
| Gate / RIG / verify 等 | 分散在上表；Gate 纯函数见 `tests/test_harness_gate.py` |

完整五层说明：[`docs/eval/02-five-layer-system.md`](../docs/eval/02-five-layer-system.md) · L2 vs L4 任务划分：[`L4-ONLY-DECISION.md`](./L4-ONLY-DECISION.md)

## 两层 eval 指标（波次 D）

| 指标 | 含义 | 状态 |
|------|------|------|
| `outcome_ok` | grading 终判通过（bug 修好了吗） | ✅ |
| `pipeline_ok` | Gate 契约 + 无 open 降级 + architecture 断言 | ✅（有 `architecture` 的任务） |
| `failure_type` | 稳定失败分类（如 `generate_patch_match`） | ✅ |
| `observability` | session + **`stage_trace`**（gate/rig/slots/locate/generate/verify 的 input/output） | ✅ |

`--strict-pipeline`：除 `outcome_ok` 外还要求 `pipeline_ok == True`。

详见 [`docs/eval/09-l4-live-probe-spec.md`](../docs/eval/09-l4-live-probe-spec.md)。

## 报告

Markdown 默认输出到 stdout；用 `-o PATH` 写入文件（推荐 `eval/runs/live/`）。

失败任务附 **结构化分步**（gate → locate → generate → verify → post_check）。JSON 内 **`observability.stage_trace`** 含各阶段完整 input/output。

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
| `fallback_open` | **历史**（7.2 后不应出现）；见 runner |

双指标：`outcome_ok`（终判）与 `pipeline_ok`（契约，仅含 `architecture` 的任务）。默认 `passed == outcome_ok`；`--strict-pipeline` 时两者皆须通过。

完整枚举：[`docs/eval/04-failure-taxonomy.md`](../docs/eval/04-failure-taxonomy.md)。

## Live 工作流

1. `ollama serve` + `ollama pull qwen2.5-coder:7b`
2. `python eval/run_eval.py --task off_by_one_sum -o eval/runs/live/...json` 单条试跑
3. 全量跑并 `--save-baseline eval/baselines/live-qwen2.5-coder-7b-post72.json`
4. 改代码后 `--compare` 看回归
5. 失败看报告 **分步结果** 或 JSON 里 **`stage_trace`**
6. 历史跑分见 [`runs/README.md`](./runs/README.md)

**说明**：Harness 单元测试（`tests/test_harness_*.py`）仍用 `FakeModelClient` 测管线接线；**eval 只测真实 agent 能力**。

不新增 pip 依赖；仅标准库 + 现有 `mini_coding_agent`。
