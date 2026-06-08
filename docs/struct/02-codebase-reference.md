# 代码架构速查

> 改动 Agent 行为前先定位自己动的是哪一层。  
> **系统总览**（端到端图、failure_type 映射）：[`ARCHITECTURE.md`](./ARCHITECTURE.md) · 本文偏**模块/符号速查**。

## 1. 仓库布局

```
mini-coding-agent-main/
├── mini_coding_agent.py          # CLI 薄入口 → mini_coding_agent.cli.main
├── mini_coding_agent/
│   ├── cli.py                    # REPL、--harness、rig build
│   ├── platform/                 # 共用底座（两种 mode 共享）
│   │   ├── tools/                # 注册表、校验、沙箱、run 管道、tool_* 实现
│   │   ├── hooks/                # HookRegistry、YAML、builtin / plugins
│   │   ├── governance.py         # diff、checkpoint、approve、回滚
│   │   ├── protocol.py           # parse / XML tool / retry
│   │   ├── prompt 相关见 modes/open/prompt.py
│   │   ├── planning.py           # make_plan
│   │   ├── skills.py             # SkillCatalog
│   │   ├── session.py            # SessionStore、CheckpointStore
│   │   ├── workspace.py          # WorkspaceContext
│   │   ├── models.py             # FakeModelClient、OllamaModelClient
│   │   ├── util.py · constants.py · wait_display.py
│   ├── modes/
│   │   ├── open/                 # Open Loop：自由工具循环
│   │   │   ├── agent.py          # MiniAgent · ask()
│   │   │   └── prompt.py         # build_prefix、build_prompt、history
│   │   └── graph/                # Graph 编排：Gate + DAG
│   │       ├── runner.py         # handle_ask 入口
│   │       ├── gate.py · gate_prompt.py
│   │       ├── slots.py          # 槽位规则（无 LLM）
│   │       ├── planner.py · executor.py · pipeline.py
│   │       ├── harness_trace.py  # stage_trace（eval 可观测）
│   │       ├── verify_rules.py   # lock_tests、pytest/py_compile
│   │       ├── session_ctx.py    # harness 会话字段
│   │       ├── nodes/            # locate / generate / verify / …
│   │       └── templates/        # 五类意图 JSON
│   └── index/                    # 离线索引：build · ensure_rig · query · store
├── eval/                         # 黄金闭环 eval（tasks.json + run_eval.py）
├── pyproject.toml
├── tests/
├── docs/
└── .github/workflows/ci.yml
```

**分层语义**：整包 = coding harness；`platform/` = 共用运行时；`modes/open` vs `modes/graph` = 两种编排路径；`index/` = 离线代码图谱。

运行时 session：`<repo_root>/.mini-coding-agent/sessions/<id>.json`  
检查点：`<repo_root>/.mini-coding-agent/checkpoints/<session>/<cp-id>.json`

**用户可见文案**：中文为主；工具名/参数/JSON 字段/`<tool>` 协议保持英文。见 [`04-user-facing-locale.md`](./04-user-facing-locale.md)（铁律 §8）。

---

## 2. 六大组件（重构后模块 map）

| # | 组件 | 关键符号 / 模块 | 职责 |
|---|------|-----------------|------|
| 1 | Live Repo Context | `platform/workspace.py` · `WorkspaceContext` | git 状态、文档片段 |
| 2 | Prompt Shape | `modes/open/prompt.py` · `build_prefix`、`build_prompt` | 稳定前缀 + 可变 transcript |
| 3 | Structured Tools | `platform/tools/*` · `protocol.parse` · `governance.approve` | 工具注册、校验、执行管道 |
| 4 | Context Reduction | `modes/open/prompt.history_text` · `platform/util.clip` | 截断、去重、压缩 |
| 5 | Transcripts & Memory | `modes/open/agent.py` · `SessionStore`、`ask` | 持久化、Open Loop 主循环 |
| 6 | Delegation | `platform/tools/implementations.tool_delegate` | 只读子 Agent |
| 7 | Graph 编排 | `modes/graph/runner.handle_ask` · Gate · pipeline · executor | 确定性 DAG（Phase 5）；Phase 7 引导 patch |
| 8 | 离线索引 | `index/build.ensure_rig` · `RigQuery` | pipeline 前自动建 `rig.db`；Locate 查询 |

---

## 3. 主循环 `ask()`（`modes/open/agent.py`）

```
用户消息 → record(user)
while tool_steps < max_steps and attempts < max_attempts:
    model.complete(prompt) → protocol.parse(raw)
    ├─ tool  → tools.runtime.run_tool(agent, …) → record → note_tool → continue
    ├─ retry → record(assistant) → continue   # 不占 tool_steps
    └─ final → record → return
```

- `attempts` 上限：`max(max_steps * 3, max_steps + 4)`
- `task`：首次 `ask` 时从用户消息截取（≤300 字符），之后不变
- `prompt()`：委托 `prompt.build_prompt(prefix, memory, history, user_message)`

---

## 4. 工具一览

| 工具 | risky | `build_tools` 有 `run` | 执行路径 |
|------|-------|------------------------|----------|
| `list_files` | 否 | 是 | `implementations.tool_list_files` |
| `read_file` | 否 | 是 | `implementations.tool_read_file` |
| `search` | 否 | 是 | `implementations.tool_search` |
| `run_shell` | **是** | 是 | `approve` → `tool_run_shell`（`shell=True`，cwd=repo_root） |
| `write_file` | **是** | **否** | **仅** `governance.run_governed_file_tool`（diff → approve → checkpoint → 写盘） |
| `patch_file` | **是** | **否** | **仅** 治理链（同上） |
| `delegate` | 否 | 是* | `implementations.tool_delegate`（*仅 `depth < max_depth` 注册） |
| `make_plan` | 否 | 是 | `implementations.tool_make_plan` → `memory.plan` |
| `load_skill` | 否 | 是 | `implementations.tool_load_skill` → `memory.loaded_skills` |

> **无** `tool_write_file` / `tool_patch_file` 直写实现；R2 已移除 dead path。

### 审批 `approval_policy`

- `ask` / `auto` / `never`；子 Agent：`read_only=True` + `never`
- 文件变更审批与 diff 预览：`governance.approve`（经 `agent.approve` 薄包装）

---

## 5. 模型输出格式（`protocol.py`）

1. JSON：`<tool>{"name":"...","args":{...}}</tool>`
2. XML：`<tool name="write_file" path="..."><content>...</content></tool>`
3. 结束：`<final>...</final>`
4. 畸形 → `retry`（`protocol.retry_notice`）

**`patch_file`（Phase 7.2）**：解析器接受 `path` + `new_text`（`old_text` 可选）。Graph fix_bug 引导模式下 **系统**从磁盘注入 `old_text`，LLM 通常只产 `new_text`。Generate 另有 ` ``` ` 代码块兜底（见 `nodes/generate.py`）。

---

## 6. 关键常量（`constants.py`）

```python
MAX_TOOL_OUTPUT = 4000
MAX_HISTORY = 12000
DOC_NAMES = ("AGENTS.md", "README.md", "pyproject.toml", "package.json")
IGNORED_PATH_NAMES = {".git", ".mini-coding-agent", "__pycache__", ...}
```

---

## 7. `run_tool` 调用链（Phase 1 + 2 + 3）

```
agent.run_tool → tools.runtime.run_tool
  → validators.validate_tool
  → validators.repeated_tool_call（防死循环）
  → invoke_tool_with_hooks（HookRegistry pre/post）
  → execute_tool_after_validation
       ├─ [plan-first] plan_first ∧ risky ∧ ¬_ask_plan_satisfied → 错误返回
       ├─ write_file | patch_file → governance.run_governed_file_tool
       │     → diff → approve(diff) → checkpoint → atomic_write_text
       │     → 失败 → governance.restore_checkpoint
       ├─ 其他 risky（如 run_shell）→ agent.approve → tool["run"](args)
       └─ safe 工具 → tool["run"](args) → implementations.*
```

**路径沙箱：** `agent.path` → `tools.sandbox.resolve_path` → `path_is_within_root`

---

## 8. Phase 3 规划热点

```
make_plan → build_planning_prompt → model.complete（单次）
  → planning.parse_plan_response → memory.plan → prompt.memory_text() 进入 prompt
```

**`--plan-first` 门控**（在 `tools/runtime.execute_tool_after_validation`，validate 之后、治理/approve 之前）：

```
若 plan_first 且 tool.risky 且非 _ask_plan_satisfied → 返回错误
否则 write/patch → 治理；run_shell → approve
```

**与 delegate：** `planning.py` 独立；`make_plan` 全 depth；`delegate` 仅 `depth < max_depth`。

详见 [`phase3.md`](./phase3.md)

---

## 9. Phase 4 Skill 热点

**Skill 目录：** `<repo_root>/.mini-coding-agent/skills/<name>/SKILL.md`

**两阶段加载：**

```
SkillCatalog.scan → prompt.build_prefix（metadata 清单，无正文）
load_skill / CLI --skills → memory.loaded_skills → prompt.memory_text()
```

**模块：** `skills.py` · **工具：** `load_skill`（safe）· **编排：** `agent._load_skill_into_memory`

详见 [`phase4.md`](./phase4.md)

---

## 10. Phase 2 Hook（含 ask/llm 扩展 · HOOK-ASK-EVENTS）

- **注册**：`agent.hook_registry` · `register_hook` / `hooks/builtin.py` · YAML `hooks.yaml`
- **事件**：
  - `pre_tool` / `post_tool` — `tools/runtime.invoke_tool_with_hooks`（校验通过之后）
  - `pre_ask` / `post_ask` — `agent.ask()` 入口 / `finally`
  - `pre_llm` / `post_llm` — 主循环每轮 prompt → complete → parse
- **Context**：`ToolHookContext` · `AskHookContext` · `LlmHookContext`（`hooks/registry.py`）
- **内置**（各可 YAML/CLI 独立启停）：

| Hook | 文件 | 配置键 |
|------|------|--------|
| session trace | `plugins/trace_hook.py` | `session_trace` |
| 终端 trace | `plugins/trace_display_hook.py` | `trace_display` |
| shell 审计 | `plugins/shell_audit_hook.py` | `shell_audit` |
| ask 耗时 jsonl | `plugins/ask_timing_hook.py` | `ask_timing` |

- **ask timing 落盘**：`<repo>/.mini-coding-agent/logs/<session_id>.jsonl`（每 ask 一行；llm/tool 交替，方案 A）

详见 [`phase2.md`](./phase2.md)

---

## 11. Graph Harness（`modes/graph/`）

**入口**：`handle_ask(agent, message, harness_enabled=…, gate_log=…)`（`runner.py`）

```
harness off 且无 gate_log → agent.ask()（无 Gate）
否则 → classify_gate (1× LLM) → record_stage("gate")
  harness on 且 route=harness_pipeline 且 intent∈五类
    → run_pipeline → ensure_rig → slots → execute_dag
    → ok: final_text | fail: 「流水线失败：reason」（不降级 open）
  其他 → agent.ask()
```

| 条件 | 行为 |
|------|------|
| `--harness off` 且无 `--gate-log` | 直接 Open |
| Gate `confidence=low` 或非法 intent | Open |
| Pipeline 节点失败 / verify retry 耗尽 | **错误返回**（Phase 7.2+） |

| 模块 | 符号 | 职责 |
|------|------|------|
| `runner.py` | `handle_ask` | Gate 分流、pipeline 调用 |
| `gate.py` | `classify_gate` | 五类意图 + confidence |
| `slots.py` | `fill_slots` | traceback/路径规则填槽（无 LLM） |
| `planner.py` | `load_template` | `templates/*.json` → DAG |
| `pipeline.py` | `run_pipeline` | `ensure_rig` + plan + execute |
| `executor.py` | `execute_dag` | 拓扑执行；verify fail → retry generate ≤2 |
| `harness_trace.py` | `record_stage` | gate/rig/slots/locate/generate/verify I/O |
| `verify_rules.py` | `lock_tests` · `run_verify_command` | eval 与 harness 共用 verify 规则 |
| `session_ctx.py` | `persist_last_gate` | `last_gate` · `harness_node_outputs` · `harness_trace` |

**fix_bug 模板**：`locate → generate → verify`（无 review）。详见 [`graph-subsystem.md`](./graph-subsystem.md) §5–6。

---

## 12. Phase 7 热点（Generate / RIG / 可观测）

| 变更 | 模块 | 说明 |
|------|------|------|
| **ensure_rig** | `index/build.py` | pipeline 启动时若无 `rig.db` 则全量 build |
| **引导 patch** | `nodes/generate.py` | fix_bug：系统读 `old_text`，LLM 只写 `new_text`；禁止 patch `tests/` |
| **retry 回滚** | `executor.py` + `verify_rules.py` | verify 失败：restore checkpoint + tests 快照后再 generate |
| **stage_trace** | `harness_trace.py` | 写入 `session.harness_trace`；eval 报告 `observability.stage_trace` |
| **无 open 降级** | `runner.py` | pipeline 失败直接返回错误 |

详见 [`phase7.md`](./phase7.md) · [`phase7.2-guided-patch.md`](./phase7.2-guided-patch.md)

---

*struct/02 · Batch 2 刷新 · 与 ARCHITECTURE / Phase 7.2 对齐 · 2026-06-08*
