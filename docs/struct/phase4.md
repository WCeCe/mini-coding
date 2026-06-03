# Phase 4：Skill 加载与可扩展工作流

> **状态**：✅ Phase 4 当前交付已结项（2026-06-02）· P4-SKILLS + P4-DOCS + P4-REVIEW  
> **前置**：Phase 1 ✅ · Phase 2 ✅ · Phase 3 ✅

---

## 1. 阶段目标

在 Phase 3 任务规划之上，补齐 **按需加载领域工作流（Skill）** 的能力：从仓库内发现 Skill、两阶段注入 prompt，使 Agent 可复用结构化指令包，而不把长 prompt 常驻 context。

**本阶段叙事（面试可讲）**：

```
启动扫描 skills/ → prefix 仅含 Skill 清单（metadata）
→ 模型 load_skill 或 CLI --skills 预加载 → 正文进 session memory → 对照 Skill 执行（仍走 Phase 1 治理）
```

---

## 1.1 P4-SKILLS ✅（2026-06-02）

| 交付 | 说明 |
|------|------|
| `skills.py` | `SkillCatalog.scan`、frontmatter、正文读取 |
| 阶段一 | `build_prefix` metadata 清单 + load_skill 规则 |
| 阶段二 | `load_skill` 工具 + CLI `--skills` → `memory.loaded_skills` |
| 测试 | 66 passed, 1 skipped |
| 验收 | [`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md) |
| 模板 | `.mini-coding-agent/skills/`（README、`SKILL.md.template`、`example-skill/`） |

## 1.2 P4-DOCS ✅

| 交付 | 说明 |
|------|------|
| README | § Skills (Phase 4)；文首 bullet；`/memory`、`/reset`；`--skills` flag |
| 验收 | [`feedback/P4-DOCS.md`](../feedback/P4-DOCS.md) |

## 1.3 P4-REVIEW ✅（2026-06-02）

| 交付 | 说明 |
|------|------|
| 独立复验 | §3.2 十条 + §3.3 五项 + README spot-check |
| 测试 | 66 passed, 1 skipped |
| 验收 | [`feedback/P4-REVIEW.md`](../feedback/P4-REVIEW.md) |

---

## 2. 范围边界

### 2.1 In Scope（按优先级）

| 优先级 | 方向 | TASK_ID | 说明 |
|--------|------|---------|------|
| **P0** | Skill 子系统架构 | P4-SKILLS | ✅ 已完成 |
| **P1** | 用户文档 | P4-DOCS | ✅ README § Skills |
| **暂缓** | Skill 高级 frontmatter | — | `allowed-tools`、`context: fork`、动态 shell 注入等 |
| **暂缓** | REPL `/skill-name` | — | 可后续单独立项 |
| **暂缓** | benchmark | — | 延续 Phase 3 策略 |

### 2.2 Out of Scope

- 兼容 `.claude/skills/` 路径（本阶段只用 `.mini-coding-agent/skills/`）
- Skill 改 Phase 1 治理语义或 Phase 2 Hook 阻断/改参
- Skill 热重载 watcher（MVP：启动/resume 时扫描即可）
- 新 pip 运行时依赖（延续 stdlib + 已有 PyYAML）
- SWE-bench、Docker 沙箱

### 2.3 已对齐产品决策

| # | 决策 | 选定 |
|---|------|------|
| 1 | Skill 目录 | `<repo_root>/.mini-coding-agent/skills/<name>/SKILL.md` |
| 2 | 加载模式 | **两阶段**：metadata 进 `build_prefix`；正文经 **`load_skill`** 或 CLI **`--skills`** |
| 3 | 与治理 | **observe-only**：只扩展 prompt / session memory |
| 4 | 与 `make_plan` | **并列**：Skill = 领域工作流；plan = 单次任务拆分 |
| 5 | 附属文件 | 不自动加载；progressive disclosure 由模型 `read_file` |

---

## 3. P4-SKILLS Done Definition

任务单见 [`command/P4-SKILLS.md`](../command/P4-SKILLS.md)。摘要如下：

### 3.1 设计概要

```
Agent 启动 / resume
  → 扫描 .mini-coding-agent/skills/*/SKILL.md
  → 解析 frontmatter（name, description）
  → 阶段一：清单写入 build_prefix（仅 metadata）

模型 load_skill(name) 或 CLI --skills foo,bar
  → 阶段二：读 SKILL.md 正文（去 frontmatter）
  → 写入 session memory.loaded_skills
  → memory_text() 展示已加载 Skill；正文进入后续 prompt
```

| 能力 | 说明 |
|------|------|
| 目录约定 | `<repo_root>/.mini-coding-agent/skills/<skill-name>/SKILL.md` |
| 阶段一 | `build_prefix` 含「可用 Skill」块：`name` + `description`（无正文） |
| 阶段二 | safe 工具 **`load_skill(name)`**；或 CLI **`--skills`** 预加载 |
| 持久化 | `session["memory"]["loaded_skills"]`；`/reset` 清空 |

### 3.2 交付清单

| # | 交付 | 要求 |
|---|------|------|
| 1 | 模块 `skills.py`（或等价） | 发现目录、解析 frontmatter、读正文、校验 skill 名 |
| 2 | `SkillCatalog` / 等价 API | 启动时扫描；目录不存在或为空时不报错 |
| 3 | frontmatter MVP | 至少 `name`（可选）、`description`（推荐）；缺省时 fallback 须在 feedback 说明 |
| 4 | 阶段一注入 | `build_prefix` 展示 Skill 清单 + 规则：相关任务先 `load_skill` |
| 5 | 工具 `load_skill` | `risky: False`；参数 `name`（必填）；失败返回明确中文错误 |
| 6 | CLI `--skills` | 逗号分隔 skill 名；Agent 构建时预加载 |
| 7 | `memory_text` | 展示已加载 Skill 信息 |
| 8 | Hook / 治理 | observe-only；不改 approve、diff、checkpoint |
| 9 | 测试 | pytest + `FakeModelClient`；覆盖发现、解析、load、CLI、reset |
| 10 | 坏文件容错 | 单个 Skill 失败跳过 + warn；不拖垮 Agent |

**明确不做（首项）**：高级 frontmatter、`` !`shell` `` 动态注入、`.claude/skills` 兼容、README 大改（另派 DOCS）。

### 3.3 可靠性契约（摘要）

| 场景 | 要求 |
|------|------|
| skills 目录不存在 | 空清单；Agent 正常启动 |
| `load_skill` 未知 name | 工具返回错误；不写 memory |
| 重复 `load_skill` 同名 | 覆盖或幂等（feedback 说明） |
| `--skills` 含未知名 | 启动 warn；已知项仍预加载 |
| 非法 YAML frontmatter | 跳过该 Skill + warn |

### 3.4 SKILL.md 最小示例

```text
.mini-coding-agent/skills/code-review/
└── SKILL.md
```

```yaml
---
name: code-review
description: 按团队标准做 PR/代码审查。用户提到 review、审查、PR 时使用。
---

# Code Review

1. 先 read_file 阅读变更范围
2. 对照 acceptance 给出分级反馈
```

---

## 4. 面试一句话

> Phase 4 加了 Skill：仓库里放 `SKILL.md` 工作流包，启动只暴露清单，用时 `load_skill` 或 `--skills` 把正文放进 session；执行仍走 Phase 1 治理与 Phase 2 trace，和 `make_plan` 并列而不是替代。

---

## 5. 任务与回报一览

| TASK_ID | 类型 | 回报 |
|---------|------|------|
| P4-SKILLS | 实现 | [`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md) ✅ |
| P4-DOCS | 文档 | [`feedback/P4-DOCS.md`](../feedback/P4-DOCS.md) ✅ |
| P4-REVIEW | 验收 | [`feedback/P4-REVIEW.md`](../feedback/P4-REVIEW.md) ✅ |

---

## 6. 代码与文档索引（首项）

| 类型 | 路径 |
|------|------|
| Skill 模块 | `mini_coding_agent/skills.py` |
| 工具 / memory / prefix | `mini_coding_agent/agent.py` |
| CLI | `mini_coding_agent/cli.py`（`--skills`） |
| 测试 | `tests/test_mini_coding_agent.py`（Phase 4 段） |
| 派活/验收 | [`command/P4-SKILLS.md`](../command/P4-SKILLS.md) · [`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md) |

---

*Phase 4 struct 文档 · P4-SKILLS + P4-DOCS + P4-REVIEW ✅*
