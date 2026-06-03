# 子 Agent 回报：P4-SKILLS

## 元信息

- **TASK_ID**: P4-SKILLS
- **TASK_TYPE**: IMPLEMENT
- **状态**: 完成

---

## 方案摘要

### 模块职责

| 模块 | 职责 |
|------|------|
| `mini_coding_agent/skills.py` | `SkillCatalog.scan`、frontmatter 解析、`read_body`、`metadata_block`、`emit_skill_warnings` |
| `mini_coding_agent/agent.py` | 启动扫描、`build_prefix` 阶段一、`load_skill` 工具、`_load_skill_into_memory`、`memory_text` 阶段二展示、`reset` 清空 |
| `mini_coding_agent/cli.py` | `--skills` 逗号分隔预加载 → `preload_skills` |

### 数据流

```
Agent 启动 / resume
  → SkillCatalog.scan(repo_root/.mini-coding-agent/skills/*/SKILL.md)
  → 坏 Skill 跳过 + stderr warn
  → build_prefix 注入 metadata 清单（无正文）
  → 可选 CLI --skills → _preload_skills → memory.loaded_skills

模型 load_skill(name)
  → read_body（去 frontmatter，strip 首尾空白）
  → memory.loaded_skills[name] = {name, description, body}
  → memory_text() / prompt() 含正文
```

### 目录与 frontmatter 约定

- 路径：`<repo_root>/.mini-coding-agent/skills/<dir>/SKILL.md`
- **name**：frontmatter `name` 优先；缺省 → **目录名**
- **description**：frontmatter `description`；缺省 → **空字符串**（清单显示「（无描述）」）
- 附属文件：不自动读入；由模型 `read_file` progressive disclosure

### `memory.loaded_skills` 形状

```python
{
  "code-review": {
    "name": "code-review",
    "description": "按团队标准做 PR/代码审查…",
    "body": "# Code Review\n1. …"  # 去 frontmatter 后的正文（strip）
  }
}
```

### `build_prefix` / `memory_text` 变更

| 位置 | 变更 |
|------|------|
| `build_prefix` | 在「有效响应示例」与「工作区」之间插入 `skill_catalog.metadata_block()`（仅 name + description + 先 load_skill 规则） |
| `memory_text` | 增加 `- loaded_skills:`：摘要行 + 各 Skill 正文块（进入 `prompt()`） |
| `build_tools` | 新增 `load_skill(name)`，`risky: False` |
| `reset` | `loaded_skills: {}` 与 plan/notes 一并清空 |

### CLI 行为

- `--skills name1,name2` → `build_agent(..., preload_skills=[...])`
- 未知名：stderr `[mini-agent] skills：预加载…` warn；已知项仍写入 memory
- 与 `--plan-first` 正交，可同时使用

### 与 `make_plan` / `delegate` 的关系

| 能力 | 作用 | 关系 |
|------|------|------|
| **Skill** | 可复用领域工作流包（SKILL.md） | 并列；不替代 plan |
| **make_plan** | 单次任务级步骤拆分 | 并列；不读 Skill 目录 |
| **delegate** | 有界只读子 Agent 调查 | 子 Agent 同样有 `load_skill` + catalog 扫描；不继承父 session 的 `loaded_skills` |

执行写文件等仍走 Phase 1 治理；Hook 仍为 observe-only。

### 重复 `load_skill` 策略

**覆盖（幂等）**：同名再次加载用磁盘最新正文覆盖 `memory.loaded_skills[name]`（MVP 无 catalog 热重载，但 `read_body` 每次读文件）。

---

## 契约对照表（struct/phase4.md §3.3）

| 场景 | 要求 | 满足 | 证据 |
|------|------|------|------|
| skills 目录不存在 | 空清单；Agent 正常启动 | ✅ | `test_skill_catalog_empty_when_dir_missing` |
| `load_skill` 未知 name | 工具返回错误；不写 memory | ✅ | `test_load_skill_unknown_name_does_not_update_memory` |
| 重复 `load_skill` 同名 | 覆盖（幂等） | ✅ | `test_load_skill_reload_overwrites_body` |
| `--skills` 含未知名 | 启动 warn；已知项仍预加载 | ✅ | `test_preload_unknown_skill_warns_but_keeps_known` |
| 非法 YAML frontmatter | 跳过该 Skill + warn | ✅ | `test_skill_catalog_skips_bad_frontmatter` |

---

## Done Definition 自证（struct/phase4.md §3.2）

| # | 交付 | 满足 | 说明 |
|---|------|------|------|
| 1 | `skills.py` | ✅ | 发现、frontmatter、正文、校验 skill 名 |
| 2 | `SkillCatalog` | ✅ | `scan`；目录空/不存在不报错 |
| 3 | frontmatter MVP | ✅ | `name`（可选）、`description`（推荐）；fallback 见上表 |
| 4 | 阶段一注入 | ✅ | `metadata_block()` + prefix 规则 |
| 5 | 工具 `load_skill` | ✅ | `risky: False`；`name` 必填；中文错误 |
| 6 | CLI `--skills` | ✅ | `_parse_skills_arg` + `preload_skills` |
| 7 | `memory_text` | ✅ | 摘要 + 正文块 |
| 8 | Hook / 治理 | ✅ | 未改 approve、diff、checkpoint、Hook 契约 |
| 9 | 测试 | ✅ | 13 项新增 + 全量 66 passed |
| 10 | 坏文件容错 | ✅ | 单 Skill warn 跳过 |

**明确未做**：高级 frontmatter、shell 动态注入、`.claude/skills`、REPL slash、热重载 watcher。

---

## 验证输出

### `python -m pytest -q`

```
66 passed, 1 skipped in 51.78s
```

（1 skipped：`test_path_rejects_symlink_escape`，环境无 symlink）

### `python -m ruff check .`

```
All checks passed!
```

---

## 变更文件一览

| 文件 | 变更类型 |
|------|----------|
| `mini_coding_agent/skills.py` | 新增 |
| `mini_coding_agent/agent.py` | Skill 扫描、工具、prefix、memory、reset |
| `mini_coding_agent/cli.py` | `--skills` |
| `tests/test_mini_coding_agent.py` | Phase 4 测试 |
| `docs/feedback/P4-SKILLS.md` | 本回报 |

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: 通过
- **独立复验**: `66 passed, 1 skipped` · `ruff check .` 绿（2026-06-02）
- **备注**: §3.2 Done Definition 10/10 满足；§3.3 可靠性契约 5/5 满足；无 scope 蔓延。Phase 4 首项结项；用户文档见 P4-DOCS（README § Skills）。

---

*P4-SKILLS · 子 Agent 回报*
