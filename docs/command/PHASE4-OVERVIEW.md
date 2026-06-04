# Phase 4 总规划（主 Agent · Skill 加载）

> 完整 Phase 4 见 [`struct/phase4.md`](../struct/phase4.md)。  
> **前置**：Phase 3 ✅（`make_plan` + `--plan-first` + 文档）

---

## 1. 阶段目标

交付 **Skill 子系统**：`.mini-coding-agent/skills/` 发现、两阶段 prompt 注入、`load_skill` 工具、CLI `--skills` 预加载。

**首项**：P4-SKILLS（架构 + 主循环衔接）。

---

## 2. 范围边界

### 2.1 In Scope（首项）

- Skill 目录扫描与 frontmatter 解析
- 阶段一：`build_prefix` metadata 清单
- 阶段二：`load_skill` + `--skills` → `memory.loaded_skills`
- pytest；Phase 1/2/3 全量回归

### 2.2 Out of Scope

- Claude Code 高级 frontmatter、动态 shell 注入、热重载
- `.claude/skills` 兼容、REPL slash 命令
- benchmark、Docker、SWE-bench
- 改 Phase 1 治理 / Phase 2 Hook 契约

### 2.3 已对齐产品决策

见 [`struct/phase4.md`](../struct/phase4.md) §2.3。

---

## 3. 工程规范（全员遵守）

| 规范 | 要求 |
|------|------|
| 依赖 | 标准库 + 已有 PyYAML + pytest；不新增运行时依赖 |
| 结构 | 改动跟着功能走；不顺手空重构 |
| 改动 | 最小必要 diff |
| 注释 | **保留**既有用户注释；**新增**代码带适量注释（铁律 §7） |
| 用户可见文案 | **中文**；工具名/参数名/frontmatter 键保持英文（铁律 §8） |
| 测试 | 新行为有 pytest；`FakeModelClient`；不依赖 Ollama |
| 验证 | `python -m pytest -q`、`python -m ruff check .` |
| Git | 不 `commit` / `push`（除非用户明确要求） |
| Hook 契约 | Phase 2 observe-only、fail-open 不变 |
| 治理 | Phase 1 diff/checkpoint/回滚语义不变 |

---

## 4. 任务一览

| TASK_ID | 目的 | 可以写代码 | 状态 |
|---------|------|------------|------|
| [P4-SKILLS](./P4-SKILLS.md) | Skill 发现 + 两阶段加载 + `load_skill` + `--skills` | 是 | ✅ |
| [P4-DOCS](./P4-DOCS.md) | README § Skills + 模板路径说明 | 否 | ✅ |
| [P4-REVIEW](./P4-REVIEW.md) | Phase 4 交付独立复验 | 否 | ✅ |

**建议顺序**：P4-SKILLS ✅ → P4-DOCS ✅ → P4-REVIEW ✅

---

## 5. 子 Agent 窗口开场白（用户复制）

```
你是本项目的子 Agent（执行者）。
请先读：
- @docs/command/PHASE4-OVERVIEW.md
- @docs/command/P4-SKILLS.md
- @docs/struct/phase4.md

在约束内自行设计 Skill 子系统并实现。
回报写入 docs/feedback/P4-SKILLS.md（含：方案摘要、契约/Done Definition 自证、pytest/ruff 输出）。
```

---

## 6. 主 Agent 验收方式

- 只对照 **Done Definition** 与 **可靠性契约**（`struct/phase4.md` §3）
- 不通过：在 `feedback` 注明差距，交同一 TASK_ID 修订
- 通过：更新 `struct/README.md` 状态板

---

*command/PHASE4-OVERVIEW · 主 Agent 维护*
