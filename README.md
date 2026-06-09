# Mini-Coding-Agent

本地 Git 工作区上的轻量编码 Agent：通过 **Ollama** 调用大模型，用结构化 tool 读/搜/写代码。CLI 入口为 `mini_coding_agent.py` 或 `mini-coding-agent`，实现包为 `mini_coding_agent/`。

**[The detailed tutorial: Components of a Coding Agent](https://magazine.sebastianraschka.com/p/components-of-a-coding-agent)**

<a href="https://magazine.sebastianraschka.com/p/components-of-a-coding-agent">
  <img src="https://substack-post-media.s3.amazonaws.com/public/images/49b97718-57f4-4977-99c8-8ad5c4d32af3_1548x862.png" width="500px">
</a>

---

## 系统架构

本项目按**分层 + 双模式编排**组织，而非按 Phase 堆叠功能。完整设计见 [`docs/struct/ARCHITECTURE.md`](docs/struct/ARCHITECTURE.md)。

### 两条执行路径

| 路径 | 触发 | 入口 | 说明 |
|------|------|------|------|
| **Open Loop**（默认） | `--harness off` | `modes/open/agent.py` → `MiniAgent.ask()` | 模型自由多轮选 tool，直到 `<final>` 或步数上限 |
| **Graph Harness** | `--harness on` 或 eval | `modes/graph/runner.py` → `handle_ask()` | Gate 分类 → 静态 DAG → 确定性节点（locate / generate / verify …） |

所有用户输入统一经 `handle_ask(agent, message, harness_enabled=…)` 路由：

```
handle_ask(message)
├── harness off 且无 --gate-log → Open Loop（无 Gate）
├── Gate confidence=low 或非法 intent → Open Loop
├── Gate high + pipeline intent → run_pipeline → 成功返回 / 失败「流水线失败：…」（不降级 Open）
└── --gate-log only → 仍跑 Gate，执行走 Open
```

> Phase 7.2 起：Pipeline 节点失败**不再**降级到 Open Loop；仅 Gate 不确定时回退 Open。

### 代码分层

```
mini_coding_agent/
├── cli.py                 # REPL、--harness、rig build
├── platform/              # 两种 mode 共用底座
│   ├── tools/             # 注册、校验、run_tool、implementations
│   ├── governance.py      # write/patch：diff → approve → checkpoint → 写盘
│   ├── protocol.py        # 解析 <tool> / <final>
│   ├── models.py          # OllamaModelClient、FakeModelClient
│   ├── session.py         # SessionStore、CheckpointStore
│   ├── planning.py        # make_plan
│   ├── skills.py          # Skill 目录扫描
│   └── hooks/             # pre/post tool、ask、llm
├── modes/
│   ├── open/              # MiniAgent.ask() 自由循环
│   │   ├── agent.py
│   │   └── prompt.py      # build_prefix、build_prompt、history
│   └── graph/             # Gate + DAG + 节点
│       ├── runner.py      # handle_ask 入口
│       ├── gate.py        # 意图分类（1× LLM）
│       ├── slots.py       # 槽位规则（无 LLM）
│       ├── planner.py     # 加载 templates/*.json
│       ├── pipeline.py    # ensure_rig → plan → execute_dag
│       ├── executor.py    # 拓扑执行、verify→generate retry
│       ├── harness_trace.py  # stage_trace（eval 可观测）
│       ├── nodes/         # locate / generate / verify / …
│       └── templates/     # 五类意图静态 DAG
└── index/                 # RIG：build / query / store（rig.db）
eval/                      # tasks.json、run_eval.py、runs/、baselines/
tests/                     # L1 diagnostic、L2 契约、harness 回归、L5 踩坑
docs/                      # struct（架构）、eval（五层规格）
```

| 层 | 职责 | 不应包含 |
|----|------|----------|
| **platform** | 工具、治理、协议、会话、Hook | 意图 / DAG 逻辑 |
| **modes/open** | 多轮对话循环 | DAG 拓扑 |
| **modes/graph** | 编排、节点、模板 | 直接写盘（须经 `run_tool`） |
| **index** | 离线 AST 图谱 | LLM 调用 |
| **eval** | 任务定义、live 探针、报告 | Agent 业务逻辑 |

### fix_bug 核心流水线

Eval 与日常修 bug 的主路径。模板 `modes/graph/templates/fix_bug.json`：`locate → generate → verify`，verify 失败最多 retry generate **2 次**。

| 步骤 | LLM? | 输入 | 输出 |
|------|------|------|------|
| Gate | 1× | user_message | intent_id, confidence, route |
| RIG | 无 | 工作区 `.py` | `rig.db`（缺失则 `ensure_rig` 自动 build） |
| slots | 无 | message + workspace | goal, files_hint, symbols_hint |
| locate | 无 | slots + RIG | files[], snippets[] |
| generate | 1× | snippets + goal + **系统注入 old_text** | patch_file / write_file |
| verify | 无 | 磁盘状态 | pytest / py_compile / lock_tests |

Generate 节点与 Open Loop 共用写盘治理链：`run_tool` → `governance.run_governed_file_tool` → diff → approve → checkpoint → atomic write。

### 五类意图与 DAG

| intent_id | 典型节点链 |
|-----------|------------|
| `fix_bug` | locate → generate → verify |
| `generate_code` | locate → generate → verify |
| `refactor` | locate → plan → generate → verify → review |
| `explain` | locate → explain |
| `project_ops` | ops |

### 持久化目录

```
<repo_root>/.mini-coding-agent/
├── sessions/<id>.json      # transcript、memory、last_gate、harness_trace
├── checkpoints/<session>/  # 写盘前快照（治理回滚）
├── rig.db                    # RIG 图谱
├── skills/<name>/SKILL.md  # 可复用 Skill
├── hooks.yaml                # Hook 配置（可选）
└── logs/<session>.jsonl      # ask timing（可选）
```

### 六大组件（与模块映射）

<a href="https://magazine.sebastianraschka.com/p/components-of-a-coding-agent">
  <img alt="Six core components of a coding agent" src="https://sebastianraschka.com/images/github/mini-coding-agent/six-components.webp" width="500px">
</a>

| # | 组件 | 模块 |
|---|------|------|
| 1 | Live Repo Context | `platform/workspace.py` |
| 2 | Prompt Shape | `modes/open/prompt.py` |
| 3 | Structured Tools | `platform/tools/*`、`protocol`、`governance` |
| 4 | Context Reduction | `modes/open/prompt.history_text`、`platform/util.clip` |
| 5 | Transcripts & Memory | `modes/open/agent.py`、`platform/session.py` |
| 6 | Delegation | `platform/tools/implementations.tool_delegate` |

Graph 编排（`modes/graph/`）与离线索引（`index/`）为 Phase 5+ 扩展，与上述六组件共用 platform 底座。

---

## 环境要求

| 依赖 | 用途 | 必需？ |
|------|------|--------|
| Python 3.10+ | 运行时 | ✅ |
| Ollama | Gate / Generate / Open 的 LLM | CLI 与 L4 eval |
| PyYAML | Hook 配置 | 可选（`pip install -e .` 已含） |
| ripgrep | `search` 加速 | 可选，有 Python 回退 |
| pytest | verify 节点、eval 终判 | 任务含 `tests/` 时 |

```bash
pip install -e .
# 或
uv sync
```

### 安装 Ollama

[ollama.com/download](https://ollama.com/download) → `ollama serve` → 拉取模型：

```bash
ollama pull qwen3.5:4b
# eval 默认模型：qwen2.5-coder:7b
```

默认 Agent 模型：`qwen3.5:4b`。Agent 调用 Ollama `POST /api/generate`。

---

## 快速开始

```bash
git clone https://github.com/rasbt/mini-coding-agent.git
cd mini-coding-agent
uv run mini-coding-agent
# 或：python mini_coding_agent.py
```

默认：`--approval ask`、`--harness off`（Open Loop）。用法示例见 [EXAMPLE.md](EXAMPLE.md)。

### Graph Harness

```bash
# 观察 Gate，执行仍走 Open
uv run mini-coding-agent --gate-log "修 calc.py 的 bug"

# 完整 Harness：Gate high → 模板流水线
uv run mini-coding-agent --harness on --approval auto "实现 hello.py"

# 构建 RIG（locate 节点用）
uv run mini-coding-agent rig build --cwd .
```

stderr 进度示例：

```text
[gate] intent_id=fix_bug confidence=high route=harness_pipeline skill=（无）
[harness] fix_bug 1/3 locate ok
[harness] fix_bug 2/3 generate ok
[harness] fix_bug 3/3 verify ok
```

### 恢复会话

```bash
uv run mini-coding-agent --resume latest
uv run mini-coding-agent --resume 20260401-144025-2dd0aa
```

### REPL 命令

| 命令 | 作用 |
|------|------|
| `/help` | 可用命令列表 |
| `/memory` | 当前 task、plan、loaded skills、tracked files |
| `/session` | 当前 session JSON 路径 |
| `/reset` | 清空 history、memory、harness 字段 |
| `/exit` / `/quit` | 退出 |

---

## 平台能力（platform/）

以下能力在 **Open Loop 与 Graph 节点内共用**。

### 写盘治理

`write_file` / `patch_file` 必须经治理链，不可直写磁盘：

```
validate_tool → run_tool → governance.run_governed_file_tool
  → diff → approve → checkpoint → atomic write → 失败则 restore_checkpoint
```

| `--approval` | 行为 |
|--------------|------|
| `ask`（默认） | 展示 unified diff 后询问 |
| `auto` | 跳过询问，仍 checkpoint + atomic write |
| `never` | 拒绝所有 risky 工具 |

Checkpoint 目录：`.mini-coding-agent/checkpoints/<session-id>/`

### Hook 可观测

工具边界事件：`pre_tool` / `post_tool`（observe-only，不阻断执行）。内置 Hook 可通过 `.mini-coding-agent/hooks.yaml` 配置：

```yaml
builtin_hooks:
  session_trace: true
  trace_display: true
  shell_audit: true
  ask_timing: false
```

模板：[`.mini-coding-agent/hooks.yaml.example`](.mini-coding-agent/hooks.yaml.example)

| CLI 覆盖 | 作用 |
|----------|------|
| `--no-trace-display` | 关闭 stderr 逐步 trace |
| `--no-session-trace` | 关闭 session `tool_trace` |
| `--no-shell-audit` | 关闭 shell 模式审计 |
| `--hooks-config PATH` | 自定义 hooks.yaml |

Hook 实现位于 `platform/hooks/plugins/`，注册见 `platform/hooks/builtin.py`。

### 任务规划（make_plan）

- **`make_plan`**：单次 LLM 调用，产出 JSON 步骤计划，写入 `memory.plan`
- **`--plan-first`**：每个 user message 在首个 risky tool 前须成功 `make_plan`
- 与 **`--harness on`** 可能冲突：Pipeline 的 generate 节点不走 ask 循环，建议 Harness 任务不用 `--plan-first`

### Skills

目录：`.mini-coding-agent/skills/<name>/SKILL.md`

- 启动时仅注入 metadata 目录；正文经 `load_skill` 或 `--skills name1,name2` 加载
- 模板：[`.mini-coding-agent/skills/SKILL.md.template`](.mini-coding-agent/skills/SKILL.md.template)

---

## Eval 体系（五层）

| 层 | 命令 | LLM | 用途 |
|----|------|-----|------|
| L1 | `pytest tests/diagnostic/` | 否 | slots / locate 组件 I/O |
| L2/L3 | `pytest tests/test_eval_contract.py` | FakeModel | DAG 契约 + grading |
| L4 | `python eval/run_eval.py` | Ollama | 真模型 fix_bug 能力 |
| L5 | `pytest tests/regression/` | FakeModel | QA_LOG 踩坑不复现 |

任务定义：`eval/tasks.json`（19 条）。Live 产物：`eval/runs/` · 基线：`eval/baselines/`

```bash
python eval/run_eval.py
python eval/run_eval.py --task syntaxerror_paren --report json -o eval/runs/live/out.json
python eval/run_eval.py --compare eval/baselines/live-qwen2.5-coder-7b-post72.json
```

Live 失败时按 `failure_type` 定位模块（详见 [`docs/struct/ARCHITECTURE.md`](docs/struct/ARCHITECTURE.md) §10）：

| failure_type | 优先查看 |
|--------------|----------|
| `gate_*` | `modes/graph/gate.py` |
| `locate_*` | `modes/graph/nodes/locate.py`, `index/query.py` |
| `generate_*` | `modes/graph/nodes/generate.py`, `platform/protocol.py` |
| `verify_*` | `modes/graph/nodes/verify.py`, `verify_rules.py` |

---

## 主要 CLI 参数

```bash
uv run mini-coding-agent --help
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--cwd` | `.` | 工作区根目录 |
| `--model` | `qwen3.5:4b` | Ollama 模型 |
| `--host` | `http://127.0.0.1:11434` | Ollama 地址 |
| `--approval` | `ask` | `ask` / `auto` / `never` |
| `--resume` | — | 恢复 session（`latest` 或 id） |
| `--max-steps` | `6` | 单轮 user message 最大 tool 步数 |
| `--max-new-tokens` | `512` | 每步生成长度上限 |
| `--plan-first` | off | risky tool 前须 make_plan |
| `--skills` | — | 启动预加载 Skill |
| `--harness` | `off` | `off` / `on` |
| `--gate-log` | off | stderr 打印 Gate 分类 |

RIG 子命令：`uv run mini-coding-agent rig build [--cwd .]`

---

## 文档导航

| 目的 | 文档 |
|------|------|
| **系统总览（推荐首读）** | [`docs/struct/ARCHITECTURE.md`](docs/struct/ARCHITECTURE.md) |
| 模块 / API 速查 | [`docs/struct/02-codebase-reference.md`](docs/struct/02-codebase-reference.md) |
| Graph 节点深描 | [`docs/struct/graph-subsystem.md`](docs/struct/graph-subsystem.md) |
| Platform 底座 | [`docs/struct/platform-subsystem.md`](docs/struct/platform-subsystem.md) |
| 当前迭代（Phase 7） | [`docs/struct/phase7.md`](docs/struct/phase7.md) |
| Eval 跑分 | [`eval/README.md`](eval/README.md) |
| 文档索引（中文） | [`docs/README.md`](docs/README.md) |
| 交互示例 | [EXAMPLE.md](EXAMPLE.md) |

---

## 说明

- 模型须输出 `<tool>...</tool>` 或 `<final>...</final>`；不同 Ollama 模型遵循度不同，弱模型可换更强的 instruction-following 模型。
- 本项目刻意保持小而可读，优先教学与架构清晰度，而非生产级鲁棒性。
- 用户可见文案以中文为主；工具名、JSON 字段、`<tool>` 协议保持英文。
