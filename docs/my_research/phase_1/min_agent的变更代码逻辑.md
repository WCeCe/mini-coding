# Mini-Agent 变更代码逻辑调研（Phase 1 / Step 1）

> 目标：梳理「模型发起写文件 → 磁盘被改动」的完整链路，标出与导师提出的「可审查变更集」之间的差距。

---

## 1. 端到端调用链（总览）

```
ask()
  → model 输出 <tool>
  → run_tool(name, args)
       → validate_tool()          # 参数校验，不改文件
       → repeated_tool_call()     # 防死循环，不改文件
       → approve()                # 人工确认，不改文件
       → tool["run"](args)         # ★ 此处直接写磁盘
  → record({role: tool, args, content: result})
  → note_tool()                    # 更新 memory.files / memory.notes
```

**核心结论**：文件变更发生在 `tool["run"](args)` 内，且 **一旦执行成功即落盘，没有 preview、checkpoint、rollback**。

---

## 2. `tool_write_file` / `tool_patch_file`

### `tool_write_file`

1. 通过 `self.path()` 解析并校验路径（必须在 workspace 内）
2. `path.parent.mkdir(parents=True, exist_ok=True)` — 自动创建父目录
3. `path.write_text(content)` — **整文件写入**
   - 文件不存在 → 新建
   - 文件已存在 → **整文件覆盖**（不是追加、不是 patch）
4. 返回 `"wrote <path> (<N> chars)"`

### `tool_patch_file`

1. 解析路径，确认目标是一个已存在的文件
2. 读取 `old_text` / `new_text`
3. 校验 `old_text` 在文件中 **必须恰好出现 1 次**（防止误替换）
4. `text.replace(old_text, new_text, 1)` 后写回
5. 返回 `"patched <path>"`

### 与 Aider SEARCH/REPLACE 的初步对比（待精读 Aider 后补充）

| 维度 | 本项目 | Aider（预期） |
|------|--------|---------------|
| 匹配方式 | 精确字符串，唯一性检查 | 多层模糊匹配 + 容错 |
| 预览 | 无 | dry-run / diff 展示 |
| 落盘时机 | approve 通过后立即写 | 预览确认后再 apply |
| 失败回滚 | 无 | checkpoint 或 git revert |

---

## 3. `approve`

`approval_policy` 三种模式（`--approval` CLI 参数）：

| 模式 | 行为 |
|------|------|
| `ask`（默认） | 终端提示 `approve <tool> <args JSON>? [y/n]`，用户输入 y/yes 才放行 |
| `auto` | 直接放行所有 risky 工具 |
| `never` | 拒绝所有 risky 工具 |

补充要点：

- `write_file` / `patch_file` / `run_shell` 均标记为 `risky: True`，会走 approve 流程
- 子 Agent（`delegate`）设置 `approval_policy="never"` 且 `read_only=True`，不能写文件
- **缺口**：approve 时展示的是 **原始 JSON 参数**（含完整 `content` 或 `old_text`/`new_text`），**不是 unified diff**，用户难以快速判断「改了什么」

---

## 4. `run_tool`

在调用 `tool["run"](args)` **之前**，以下情况 **不会改动磁盘**：

- 未知工具名
- `validate_tool()` 参数校验失败
- `repeated_tool_call()` 检测到连续重复调用
- `approve()` 被拒绝

在调用 `tool["run"](args)` **之后**：

- **成功** → 文件已变更，无法撤销
- **抛异常** → 返回 `error: tool <name> failed: ...`；对已存在的文件，单次 `write_text` / 读-改-写通常是原子操作，一般不会留下半写状态，但 **没有显式回滚逻辑**

---

## 5. `SessionStore` + `record` / `note_tool`

### `record`

每次工具调用后写入 `session["history"]`，结构为：

```json
{
  "role": "tool",
  "name": "write_file",
  "args": { "path": "...", "content": "..." },
  "content": "wrote demo.py (42 chars)",
  "created_at": "..."
}
```

- `args` 保存 **完整调用参数**（含整文件 content）
- `content` 保存工具返回的 **一行结果摘要**
- 随后 `SessionStore.save()` 落盘到 `.mini-coding-agent/sessions/<id>.json`

### `note_tool`

- `memory["files"]`：记录操作过的文件路径（最多 8 条）
- `memory["notes"]`：记录 `"write_file: wrote ..."` 这类摘要（最多 5 条）

### `history_text`（喂给模型的 transcript）

- 工具条目格式：`[tool:write_file] {"content": "...", "path": "..."}` + 结果摘要
- 对 `write_file` / `patch_file` 会 **取消** 对应路径的 read 去重，避免模型看不到自己刚改过的文件上下文
- **没有 diff 字段**；但大文件的 **完整 content 会出现在 args 的 JSON 里**（有截断：`recent` 900 字符 / 旧记录 180 字符）

---

## 6. `WorkspaceContext.build`

- 启动时执行一次 `git status --short`、`git log --oneline -5`、读项目文档
- 结果注入 prompt 前缀（`workspace.text()`），供模型了解仓库状态
- **只读**：不执行 commit、push、stash、revert 等任何写操作
- **注意**：workspace 快照在 Agent 初始化时构建（`main()` 里 `WorkspaceContext.build(args.cwd)`），**会话过程中不会刷新** —— 模型看到的 git status 可能是过时的

---

## 7. 现状 vs 目标差距（给 Aider 精读的对照表）

| 能力 | 现状 | 导师目标 |
|------|------|----------|
| 变更形式 | 裸写文件 / 精确替换 | 可审查的变更集（diff-first） |
| 用户确认 | 看 JSON 参数点 y/n | 看 unified diff 再批准 |
| 事务边界 | 无 | per-ask checkpoint |
| 回滚 | 无 | rollback 到 checkpoint 或 git |
| Git 集成 | 只读 status/log | diff 预览，可选 auto-commit |
| 失败恢复 | 报错字符串 | 匹配失败反馈 + 不破坏磁盘状态 |

---

## 8. 下一步：精读 Aider 时带着这 4 个问题

读 Aider 源码时，逐条找答案并回填到本文档第 2 节对比表：

1. Aider 的变更是在哪一步从「计划」变成「落盘」的？
2. 用户拒绝编辑时，磁盘状态变了吗？
3. 回滚靠内部 backup 还是 git？
4. SEARCH/REPLACE 匹配失败时，给模型什么反馈？
