# 子 Agent 回报：P1-CHANGE-GOVERNANCE

## 元信息

- **TASK_ID**: P1-CHANGE-GOVERNANCE
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成（README 留给 P1-DOCS）

---

## 方案摘要

在 `run_tool` 内对 `write_file` / `patch_file` 走独立治理链路，不改模型 tool 协议：

```
validate → repeated_check
  → 读磁盘 fresh → 算 proposed content → difflib unified diff
  → refresh git status → approve(diff) 
  → checkpoint 落盘 → atomic_write_text
  → 失败则 _restore_checkpoint
```

**新增组件（单文件内）**

| 符号 | 职责 |
|------|------|
| `atomic_write_text` / `text_sha256` / `file_sha256` | 原子写与哈希校验 |
| `build_unified_diff` / `diff_summary` | diff 生成与摘要 |
| `CheckpointStore` | `.mini-coding-agent/checkpoints/<session>/<cp-id>.json` |
| `WorkspaceContext.refresh_git_status` / `git_dirty_warning` | 审批前脏树提示 |
| `MiniAgent._run_governed_file_tool` | 治理主流程 |
| `MiniAgent._restore_checkpoint` | 回滚（含新建文件删除、外部修改 skip） |

**session 审计**：`ask()` 记录 tool 时合并 `_last_tool_meta`（`diff_summary`、`checkpoint_id`、`rolled_back`）。

`run_shell` 仍走原 `approve(name, args)`，无 diff。

---

## 契约与 Done Definition 自证

| 条目 | 满足 | 证据 |
|------|------|------|
| 审批展示 unified diff | ✅ | `test_approve_shows_diff_not_raw_json` |
| 拒绝 → 磁盘不变 | ✅ | `test_approval_denied_leaves_file_unchanged` |
| 写盘失败 → 自动回滚 | ✅ | `test_write_failure_rolls_back_new_file`, `test_patch_failure_restores_original_content` |
| 新建失败回滚 → 文件不存在 | ✅ | `test_write_failure_rolls_back_new_file` |
| 脏 git → 审批警告 | ✅ | `test_git_dirty_warning_shown_on_approval` |
| `run_shell` 行为不变 | ✅ | `test_run_shell_approval_unchanged` |
| checkpoint 失败不写盘 | ✅ | 代码：`save` 异常直接 return，不调 `atomic_write_text` |
| 外部修改 → skip 回滚 | ✅ | `test_restore_skips_when_file_modified_externally` |
| session 可审计 | ✅ | `test_ask_records_governance_metadata_in_history` |
| pytest 全绿 | ✅ | 见下方 |
| ruff | ✅ | 见下方 |
| 单文件主逻辑 | ✅ | 仅改 `mini_coding_agent.py` + `tests/` |
| README Change Governance | ⏳ | 由 **P1-DOCS** 任务交付 |

---

## 交付物

- `mini_coding_agent.py` — 变更治理实现
- `tests/test_mini_coding_agent.py` — 8 个新用例 + 回归

---

## 验证结果

```
python -m pytest -q
27 passed, 1 skipped

python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- diff 过长时终端仅完整打印（未分页）；history 存 `diff_summary` 截断版
- 非 git 仓库无脏树警告（`git status` 失败视为 clean）
- `validate_tool(patch_file)` 与治理层各读一次文件，极端 TOCTOU 未完全消除

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**（任务级；Phase 1 整体仍待 P1-DOCS / P1-REVIEW）
- **备注**:
  - 独立复验：`27 passed, 1 skipped`，`ruff` 通过（2026-05-29）
  - Done Definition §4.1 功能六项、`§4.2` 前三项（pytest / ruff / 单文件）均满足
  - `struct/05` 可靠性契约六项均可在代码或测试中对应
  - 约束遵守：未改 `parse`/tool 协议；`run_shell` 仍走原 approve；无新 pip 依赖
  - 非阻塞建议：`tool_write_file`/`tool_patch_file` 仍保留直写路径但 `run_tool` 已 bypass，后续可标 private 或删 dead path；`auto` 模式不打印 diff 可接受（无交互审批）
  - README 未完成属预期，交 **P1-DOCS**
