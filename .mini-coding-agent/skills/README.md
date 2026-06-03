# Skills 目录说明

本目录存放 **Mini-Coding-Agent** 的项目级 Skill（Phase 4）。

## 目录约定

```text
.mini-coding-agent/skills/
├── README.md              # 本说明（Agent 不加载）
├── SKILL.md.template      # 复制后改名为 <你的-skill>/SKILL.md
└── example-skill/         # 可运行的示例 Skill
    └── SKILL.md
```

每个 Skill 占一个子目录，且必须包含 **`SKILL.md`**。Skill 名称默认取**目录名**；也可在 frontmatter 里写 `name:`（须与目录名一致或你自行约定，扫描以解析后的 `name` 为准）。

## 两阶段加载

| 阶段 | 内容 | 何时 |
|------|------|------|
| **一** | `name` + `description` 清单 | Agent 启动时进入 prompt 前缀 |
| **二** | SKILL.md 正文 | 模型调用 `load_skill`，或 CLI `--skills` 预加载 |

## 快速开始

1. 复制模板：

   ```bash
   cp -r .mini-coding-agent/skills/example-skill .mini-coding-agent/skills/my-skill
   # 或：复制 SKILL.md.template 到新目录并编辑
   ```

2. 编辑 `my-skill/SKILL.md` 的 `description`（写清**做什么**与**何时用**）。

3. 启动 Agent 并加载：

   ```bash
   python mini_coding_agent.py --skills my-skill "按 Skill 执行任务"
   ```

   或在对话中让模型调用：

   ```text
   <tool>{"name":"load_skill","args":{"name":"my-skill"}}</tool>
   ```

4. REPL 中 `/memory` 可查看已加载 Skill 摘要与正文。

## 与 `make_plan` 的关系

- **Skill**：可复用的领域工作流指令（长期维护的 SKILL.md）。
- **make_plan**：针对当前用户目标的一次性任务拆分。

二者并列，互不替代。写文件仍走 Phase 1 变更治理。

## 附属文件

除 `SKILL.md` 外的文件**不会**自动加载；在正文中用相对路径说明，由 Agent `read_file` 按需读取。

更多说明见仓库根目录 [`README.md`](../../README.md) § Skills (Phase 4)。
