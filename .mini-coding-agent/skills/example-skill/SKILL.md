---
name: example-skill
description: 演示 Mini-Coding-Agent Skill 两阶段加载的示例工作流。用户提到「示例 Skill」「example-skill」或想了解如何编写 Skill 时使用。
---

# 示例 Skill（example-skill）

本 Skill 随仓库提供，用于演示 **Phase 4** 行为；可直接 `--skills example-skill` 预加载，或由模型 `load_skill`。

## 目标

用最小步骤说明当前仓库里 Skill 目录的作用，并给出一份简短检查清单。

## 步骤

1. 用 `list_files` 或 `read_file` 查看 `.mini-coding-agent/skills/README.md`（若路径存在）。
2. 向用户说明：
   - 阶段一：启动时 prefix 只显示 Skill **清单**（name + description）
   - 阶段二：`load_skill` 或 `--skills` 才把**正文**写入 `memory.loaded_skills`
3. 提醒用户复制 `SKILL.md.template` 或 `example-skill/` 目录创建自己的 Skill。
4. 说明与 `make_plan` 并列：复杂任务可先 `make_plan` 再按 Skill 执行，二者不互相替代。

## 输出格式

用简短中文回复，包含：

- 已加载的 Skill 名称
- 两阶段加载的一句话解释
- 指向 `skills/README.md` 的下一步建议

## 明确不做

- 不要修改仓库代码或运行 risky 工具，除非用户明确要求
- 不要声称实现了 Claude Code 的高级 Skill frontmatter（如 `allowed-tools`）
