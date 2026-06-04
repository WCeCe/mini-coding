# 任务单：P4-SKILLS

## 元信息

- **TASK_ID**: P4-SKILLS
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: Phase 1 ✅ · Phase 2 ✅ · Phase 3 ✅

---

## 目标

交付 **Skill 子系统架构**：从 `<repo_root>/.mini-coding-agent/skills/` 发现 Skill，**两阶段**注入主循环——阶段一把 metadata 清单放进 `build_prefix`；阶段二通过 **`load_skill` 工具** 或 CLI **`--skills`** 加载正文到 session memory。

达到 [`struct/phase4.md`](../struct/phase4.md) §3 Done Definition。本项只建架构与衔接，不做 Claude Code 高级特性。

---

## 约束（必须遵守）

- 见 [`PHASE4-OVERVIEW.md`](./PHASE4-OVERVIEW.md) §3 工程规范
- **目录**：`<repo_root>/.mini-coding-agent/skills/<skill-name>/SKILL.md`（skill 名默认取目录名；frontmatter `name` 可选）
- **两阶段**：
  - 阶段一：仅 `name` + `description` 进 prefix，**不含** SKILL.md 正文
  - 阶段二：`load_skill(name)` 或 `--skills` 预加载 → 正文进 `session["memory"]["loaded_skills"]`
- **`load_skill` 为 safe tool**（`risky: False`）；不触发 approve；不走 write/patch/shell
- **observe-only**：Skill 只扩展 prompt / memory，**不**改 Phase 1 治理、**不**改 Phase 2 Hook 契约、**不**增删工具 schema（除 `load_skill` 本身）
- **附属文件**：Skill 目录内除 `SKILL.md` 外文件不自动读入；progressive disclosure 留给模型 `read_file`
- **容错**：单个坏 Skill 跳过 + warn（参考 hooks 配置 warn 模式）；目录缺失不 fatal
- **`/reset`**：清空 `loaded_skills`（与 plan/notes 等 memory 一并重置）
- **frontmatter MVP**：`name`、`description`；其他 Claude Code 字段本项**不实现**
- **保留用户注释** + **新增代码带注释**（铁律 §7）
- **用户可见文案中文**；工具名/参数名/frontmatter 键保持英文

---

## 交付物

1. 代码：`mini_coding_agent/skills.py`（或你设计的等价模块）、`agent.py`、`cli.py`、`tests/`；测试 fixture 可含示例 `SKILL.md`
2. 回报：[`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md)，须包含：
   - **方案摘要**（模块职责、数据流、memory 形状、`build_prefix` / `memory_text` 变更、CLI 行为）
   - **契约对照表**（对照 struct §3.3）
   - **Done Definition 自证**（逐条 §3.2）
   - **与 make_plan / delegate 的关系说明**（并列、不互相替代）
   - `pytest -q` 与 `ruff check .` 输出

---

## 验收标准

- [ ] 扫描 `.mini-coding-agent/skills/*/SKILL.md`；目录空/不存在时 Agent 正常启动
- [ ] `build_prefix` 含可用 Skill 清单（仅 metadata）及「相关时先 load_skill」规则
- [ ] `load_skill(name)` 成功加载正文到 memory；未知名/坏文件返回明确中文错误
- [ ] CLI `--skills name1,name2` 构建 Agent 时预加载对应 Skill
- [ ] `memory_text()` 与 `/memory` 可见已加载 Skill 信息
- [ ] `/reset` 清空 loaded skills
- [ ] pytest 覆盖发现、解析、load、CLI、reset；`FakeModelClient`；Phase 1/2/3 既有用例仍绿
- [ ] `ruff check .` 通过
- [ ] 无 scope 蔓延（无 allowed-tools、无 slash 命令、无 `.claude/skills` 兼容、无 README 大改）

---

## 参考资料

- [`struct/phase4.md`](../struct/phase4.md) §3 — Done Definition · 可靠性契约
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) — `build_prefix`、`memory_text`、`prompt` 形状
- [`mini_coding_agent/planning.py`](../../mini_coding_agent/planning.py) — 独立模块先例
- [`mini_coding_agent/cli.py`](../../mini_coding_agent/cli.py) — `--plan-first` 旗标模式
- [Claude Code Skills 文档](https://code.claude.com/docs/en/skills) — 概念参考（不必 1:1 实现）

---

*实现路径由子 Agent 自定*
