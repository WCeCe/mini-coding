# 项目愿景与路线图

## 1. 项目是什么

**Mini-Coding-Agent**：极简本地编码 Agent，通过 Ollama 调用本地大模型，在指定 Git 工作区内以工具循环完成读代码、搜索、写文件、跑 shell 等任务。

| 属性 | 说明 |
|------|------|
| 当前形态 | 包 `mini_coding_agent/` + CLI 入口 `mini_coding_agent.py` |
| 目标形态 | **找工作用的作品集** — 可展示、可讲解、可度量 |
| 运行时依赖 | Python 标准库（测试用 pytest） |
| 模型后端 | Ollama `POST /api/generate` |

---

## 2. 总目标

把教学级 demo 演进为能回答面试官核心问题的 coding agent：

- 模型写错代码怎么办？
- 如何避免把仓库改坏？
- 上下文有限时如何管理 transcript？
- 如何证明 agent 变好了？（后续阶段）

---

## 3. 与成熟项目的差距（优先级排序）

| 优先级 | 差距 | 阶段 |
|--------|------|------|
| P0 | 无 diff 预览、无 checkpoint/回滚 | ~~Phase 1~~ ✅ |
| P1 | 无可观测性（trace、耗时） | ~~Phase 2~~ ✅ 轻量 |
| P1 | 无 benchmark / 回归任务集 | **暂缓**（coding 链路设计稳后再做） |
| P2 | `run_shell` 全权限、无阻断 | 部分（Phase 2 仅审计告警） |
| P2 | 单文件、无扩展点 | ~~Phase 2~~ ✅ 已拆包 + Hook |
| P3 | 仅 Ollama、非流式 | 按需 |
| P0 | LLM 每步自选 tool（无图式编排） | ~~Phase 5~~ ✅ Graph 编排 |

**结论**：Phase 1–5 已补齐治理、可观测、规划、Skill、Graph 编排与 eval 基线。后续见 [`phase5-graph.md`](./phase5-graph.md) §9（5.8+）。

---

## 4. 阶段规划

### Phase 1 — 变更治理 ✅

详见 [`phase1.md`](./phase1.md)。

### Phase 2 — Hook + 可观测 + 重构 ✅

含：工具边界 Hook、包重构、终端 trace、shell 审计、YAML 配置。详见 [`phase2.md`](./phase2.md)。

### Phase 3 — 任务规划 + coding 链路深度 ✅

`make_plan` + `--plan-first` + 文档已结项。benchmark 量化暂缓。详见 [`phase3.md`](./phase3.md)。

### Phase 4 — Skill 加载与可扩展工作流 ✅

P4-SKILLS + P4-DOCS + P4-REVIEW 已结项。详见 [`phase4.md`](./phase4.md)。

### Phase 5 — Graph 编排（确定性 DAG）✅

Gate + 模板 DAG + Executor + index + eval 黄金闭环。详见 [`phase5-graph.md`](./phase5-graph.md)。

---

## 5. 铁律

1. **边界未清先问、不得擅下定论**（**主 Agent 首要**）— 对用户的每一要求，若在**产品/架构决策**（如阶段归属、是否替换现有能力、专家/模块划分、In/Out Scope 定稿）或**分析性结论**（如「合理/不合理」「建议某 Phase」「推荐某方案为默认」）上存在未确认边界或模棱两之处，**须先向用户反问澄清**；**未获明确答复前**，不得写入 `struct/` 定稿、不得派 `command/`、不得把假设表述为已对齐结论。若需列出候选，须显式标注 **「待确认 / 非定论」**，并在回复末尾**集中提问**。
2. **主 Agent 与用户意见一致之前，不生成 Phase 1 实现代码。**
3. **不以空重构开场** — 拆文件跟着功能走。
4. **标准库优先** — 新依赖须主 Agent 与用户批准（Phase 2 已批准 **PyYAML**）。
5. **新行为必有 pytest** — 用 `FakeModelClient`，不依赖 Ollama。
6. **保留用户注释** — 除非对应代码逻辑**完全删除**，否则不得随意删改既有注释；重构迁代码时须一并带走注释，过时注释可改措辞但勿静默移除。
7. **新增代码须有注释** — 生成或改动的代码应带**适量**注释，说明模块职责、非显而易见的设计选择与关键分支；服务于可读性，不堆砌废话，也不写逐行机械解说。
8. **用户可见文案用中文** — 面向用户与模型的说明性文字（prompt 规则、工具 description、错误/成功返回、`ValueError` 文案、CLI help、审批提示、REPL 帮助等）使用**中文**；**工具名、参数名、JSON 字段名、`<tool>`/`<final>` 协议标签**等代码/协议标识保持**英文**。细则见 [`04-user-facing-locale.md`](./04-user-facing-locale.md)。

---

## 6. Phase 1 明确不做

- 拆包大重构（第一版）
- OpenAI / Claude 多模型
- LSP、网页搜索等新 tool
- 华丽 TUI / Web UI
- Docker 沙箱
- SWE-bench
- 自动 `git commit`

---

*struct/01 · 主 Agent 维护*
