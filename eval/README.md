# 黄金闭环 Eval

可重复度量 `fix_bug` 路径：`handle_ask(..., harness_enabled=True)` + 隔离临时仓库 + 文件/verify 断言。

契约见 [`docs/struct/phase5-graph.md`](../docs/struct/phase5-graph.md) §7（Eval 与黄金闭环）。

## 前置

| 模式 | 要求 |
|------|------|
| **--fake**（CI / 回归） | Python 3.10+，与主仓库相同依赖；**无需** Ollama |
| **--live** | 本机 `ollama serve` 已启动；已 `ollama pull` 目标模型（默认 `qwen2.5-coder:7b`） |

建议 live 前先用 Fake 全绿：

```bash
python eval/run_eval.py --fake
```

## 用法

在仓库根目录执行：

```bash
# FakeModel 回归（推荐 CI）
python eval/run_eval.py --fake

# 仅跑一条任务
python eval/run_eval.py --fake --task nameerror_calc

# CSV 报告
python eval/run_eval.py --fake --report csv

# 真实 Ollama（须本机 Ollama；首次基线见 feedback/GL-5-LIVE-EVAL.md）
python eval/run_eval.py --live --model qwen2.5-coder:7b

# 调大超时 / token（慢模型或复杂 patch）
python eval/run_eval.py --live --ollama-timeout 180 --max-new-tokens 768
```

退出码：`0` 全部 pass；`1` 存在 fail；`2` live 预检失败（Ollama 未就绪）。

框架单测：

```bash
python -m pytest tests/test_eval_runner.py -q
```

## 与 CLI 的关系

交互式调试可用主 CLI（须显式开 harness）：

```bash
python -m mini_coding_agent.cli --harness on --approval auto
```

Eval 脚本**不**走 CLI，直接 `handle_ask(agent, message, harness_enabled=True)`，与黄金闭环单测一致。

## Agent 约定

- `approval_policy=auto`（补丁不经交互审批）
- `enable_trace_hook=False`（减少 eval 噪声）
- 每任务独立 `tempfile` 目录，写入 `setup_files` 后调用 harness
- **--live** 使用 `OllamaModelClient`（`models.py`），与 CLI 默认模型/host 可对齐

## tasks.json（当前 5 条）

| id | 场景 | verify |
|----|------|--------|
| `nameerror_calc` | Traceback NameError，`calc.py` | py_compile |
| `syntaxerror_paren` | 未闭合括号 SyntaxError | py_compile |
| `nameerror_greet` | `greet.py` 未定义变量 | py_compile |
| `off_by_one_sum` | `range` 上界 off-by-one + pytest | pytest |
| `wrong_operator_calc` | 误用 `-` 应为 `+` | py_compile |

### 字段

| 字段 | 含义 |
|------|------|
| `id` | 任务唯一 id |
| `description` | 人类可读说明 |
| `message` | 传给 `handle_ask` 的用户消息 |
| `setup_files` | eval 前写入临时仓库的相对路径 → 内容 |
| `expect_files` | 执行后须 **精确匹配** 的文件内容 |
| `verify` | `py_compile` \| `pytest` \| `none`（任务级复核，与 harness verify 并存） |
| `harness_intent` | Golden Loop 阶段仅 `fix_bug` |

## FakeModel 队列

`--fake` 按 `setup_files` / `expect_files` 自动推导（GL-4 后 **无 review**）：

1. Gate JSON（`fix_bug` + `high`）
2. `patch_file`（最小 diff；多文件 expect 则多次 patch）

## 报告

Markdown 默认输出到 stdout：`task_id`、pass/fail、失败环节、原因、耗时(ms)。失败时附 **Harness stderr 摘要**。

### 读 stderr 定位失败步（phase5-graph §7.4）

| stderr / 原因模式 | 失败步 |
|-------------------|--------|
| `confidence=low` / `route=open` | Gate |
| `locate fail` / `1/3 locate` | Locate |
| `generate 须返回 tool` / `generate 仅允许` | Generate |
| `verify fail` / `3/3 verify fail` | Verify 或 Generate 改错 |
| `流水线失败` / `降级 open` | pipeline |
| `内容与期望不符` | expect_files（post_check） |
| `py_compile 失败` / `pytest 失败` | verify（任务级复核） |

典型进度行：

```
[harness] fix_bug 1/3 locate ok
[harness] fix_bug 2/3 generate ok
[harness] fix_bug 3/3 verify ok
```

## Live 基线工作流

1. `python eval/run_eval.py --fake` → 5/5 pass  
2. `ollama serve` + `ollama pull qwen2.5-coder:7b`  
3. `python eval/run_eval.py --live` → 记录通过率；失败看报告中的失败环节与 stderr 摘要  
4. 只改对应环节（Locate / Generate / Verify / 模板），再跑对比  

不新增 pip 依赖；仅标准库 + 现有 `mini_coding_agent`。
