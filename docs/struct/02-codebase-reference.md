# 代码架构速查

> 改动 `mini_coding_agent.py` 前先定位自己动的是哪一层。

## 1. 仓库布局

```
mini-coding-agent-main/
├── mini_coding_agent.py
├── pyproject.toml
├── tests/test_mini_coding_agent.py
├── docs/                    # 本文档体系
└── .github/workflows/ci.yml
```

运行时 session：`<repo_root>/.mini-coding-agent/sessions/<id>.json`

**用户可见文案**：中文为主；工具名/参数/JSON 字段/`<tool>` 协议保持英文。见 [`04-user-facing-locale.md`](./04-user-facing-locale.md)（铁律 §7）。

---

## 2. 六大组件

| # | 组件 | 关键符号 | 职责 |
|---|------|----------|------|
| 1 | Live Repo Context | `WorkspaceContext` | git 状态、文档片段 |
| 2 | Prompt Shape | `build_prefix`, `memory_text`, `prompt` | 稳定前缀 + 可变 transcript |
| 3 | Structured Tools | `build_tools`, `run_tool`, `validate_tool`, `approve`, `parse` | 工具、校验、审批、解析 |
| 4 | Context Reduction | `clip`, `history_text` | 截断、去重、压缩 |
| 5 | Transcripts & Memory | `SessionStore`, `record`, `note_tool`, `ask`, `reset` | 持久化、主循环 |
| 6 | Delegation | `tool_delegate` | 只读子 Agent |

---

## 3. 主循环 `ask()`

```
用户消息 → record(user)
while tool_steps < max_steps and attempts < max_attempts:
    model.complete(prompt) → parse(raw)
    ├─ tool  → run_tool → record → note_tool → continue
    ├─ retry → record(assistant) → continue   # 不占 tool_steps
    └─ final → record → return
```

- `attempts` 上限：`max(max_steps * 3, max_steps + 4)`
- `task`：首次 `ask` 时从用户消息截取（≤300 字符），之后不变

---

## 4. 工具一览

| 工具 | risky | 说明 |
|------|-------|------|
| `list_files` | 否 | 列目录 |
| `read_file` | 否 | 按行号读 UTF-8 |
| `search` | 否 | 有 `rg` 用 ripgrep，否则 Python 回退 |
| `run_shell` | **是** | `shell=True`，cwd=repo_root |
| `write_file` | **是** | 直接覆盖写 |
| `patch_file` | **是** | `old_text` 唯一匹配 |
| `delegate` | 否 | 子 Agent；`depth < max_depth` 才注册 |
| `make_plan` | 否 | 单次规划调用；结构化任务拆分；写入 `memory.plan` |
| `load_skill` | 否 | 加载 `.mini-coding-agent/skills/` Skill 正文 → `memory.loaded_skills` |

### 审批 `approval_policy`

- `ask` / `auto` / `never`；子 Agent：`read_only=True` + `never`

---

## 5. 模型输出格式

1. JSON：`<tool>{"name":"...","args":{...}}</tool>`
2. XML：`<tool name="write_file" path="..."><content>...</content></tool>`
3. 结束：`<final>...</final>`
4. 畸形 → `retry`

---

## 6. 关键常量

```python
MAX_TOOL_OUTPUT = 4000
MAX_HISTORY = 12000
DOC_NAMES = ("AGENTS.md", "README.md", "pyproject.toml", "package.json")
IGNORED_PATH_NAMES = {".git", ".mini-coding-agent", "__pycache__", ...}
```

---

## 7. Phase 1 改造热点

**当前文件修改链：**
```
parse → ask → run_tool → approve → tool_write_file / tool_patch_file
```

**治理插入点（见 `phase1.md`）：**
```
run_tool → validate → repeated_tool_call
  → [write_file/patch_file] diff → approve(diff) → checkpoint → atomic write
  → [run_shell] 保持现有 approve
```

**路径沙箱：** `path()` → `resolve()` → `path_is_within_root(repo_root)`

---

## 8. Phase 3 改造热点（首项）

**规划工具链：**

```
make_plan → build_planning_prompt → model.complete（单次）
  → parse_plan_response → memory.plan → memory_text() 进入 prompt
```

**`--plan-first` 门控（在 approve / 治理之前）：**

```
run_tool → validate → _execute_tool_after_validation
  → 若 plan_first 且 risky 且非 _ask_plan_satisfied → 返回错误
  → 否则 write/patch → 治理；run_shell → approve
```

**与 delegate：** `planning.py` 独立模块；`make_plan` 全 depth 可用；`delegate` 仅 `depth < max_depth`。

详见 [`phase3.md`](./phase3.md) · [`README.md`](../README.md) § Task Planning

---

## 9. Phase 4 Skill 热点（P4-SKILLS ✅）

**Skill 目录：** `<repo_root>/.mini-coding-agent/skills/<name>/SKILL.md`

**两阶段加载：**

```
SkillCatalog.scan → build_prefix metadata 清单
load_skill(name) / CLI --skills → memory.loaded_skills → memory_text()
```

**模块：** `mini_coding_agent/skills.py` · **工具：** `load_skill`（safe）

详见 [`phase4.md`](./phase4.md) · [`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md)

---

*struct/02 · 随代码演进更新*
