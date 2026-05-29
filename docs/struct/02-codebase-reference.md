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

**计划插入点（见 `05-phase1-implementation-design.md`）：**
```
run_tool → validate → repeated_tool_call
  → [write_file/patch_file] diff → approve(diff) → checkpoint → atomic write
  → [run_shell] 保持现有 approve
```

**路径沙箱：** `path()` → `resolve()` → `path_is_within_root(repo_root)`

---

*struct/02 · 随代码演进更新*
