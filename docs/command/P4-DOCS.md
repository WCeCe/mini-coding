# 任务单：P4-DOCS

## 元信息

- **TASK_ID**: P4-DOCS
- **TASK_TYPE**: DOCS
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P4-SKILLS ✅

---

## 目标

在根 [`README.md`](../../README.md) 中补充 **Phase 4 Skill** 用户说明：目录约定、两阶段加载、`load_skill` 与 CLI `--skills`、session memory 行为；与 `make_plan` 分工一句话。

仓库内已提供模板与示例（主 Agent 创建，子 Agent 须在 README 中引用路径）：

- [`.mini-coding-agent/skills/README.md`](../../.mini-coding-agent/skills/README.md)
- [`.mini-coding-agent/skills/SKILL.md.template`](../../.mini-coding-agent/skills/SKILL.md.template)
- [`.mini-coding-agent/skills/example-skill/SKILL.md`](../../.mini-coding-agent/skills/example-skill/SKILL.md)

---

## 约束

- **仅文档** — 不改 `mini_coding_agent/` 业务逻辑（`.mini-coding-agent/skills/` 模板已存在，无需再建除非发现路径错误）
- 与 [`struct/phase4.md`](../struct/phase4.md)、[`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md) 一致
- 说明 **`load_skill` vs `make_plan` vs `delegate`** 分工（各一句话）
- 不展开高级 frontmatter、REPL slash、`.claude/skills` 兼容、benchmark
- 保持 README 现有结构与语气（英文 README；可与 Phase 3 § Task Planning 并列新增 **§ Skills (Phase 4)**）
- Feature 列表（文首 bullet）增加 Skill 一行
- CLI 参考表增加 `--skills` 条目
- 不重复 struct / feedback 全文

---

## 交付物

- 更新 [`README.md`](../../README.md)
- 回报：[`feedback/P4-DOCS.md`](../feedback/P4-DOCS.md)（改了哪些章节、自检清单）

---

## 验收标准

- [ ] README 含 **Skills (Phase 4)** 章节（或等价标题）
- [ ] 说明目录 `.mini-coding-agent/skills/<name>/SKILL.md` 与 frontmatter `name` / `description`
- [ ] 说明两阶段：启动 metadata 清单 vs `load_skill` / `--skills` 加载正文
- [ ] 含 `load_skill` 工具表（risky、参数 `name`、调用示例）
- [ ] 含 `--skills` 示例命令（可与 `--plan-first` 并存）
- [ ] 说明 `/memory`、session 中 `memory.loaded_skills`、`/reset` 清空
- [ ] 指向仓库内 `skills/README.md` 与 `example-skill` 模板
- [ ] 无与实现不符的声称
- [ ] feedback 落盘至 [`feedback/P4-DOCS.md`](../feedback/P4-DOCS.md)

---

## 参考资料

- [`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md)
- [`struct/phase4.md`](../struct/phase4.md) §4 面试一句话
- [`.mini-coding-agent/skills/README.md`](../../.mini-coding-agent/skills/README.md)
- README 现有 § Task Planning (Phase 3)（结构与语气参考）

---

*实现路径由子 Agent 自定*
