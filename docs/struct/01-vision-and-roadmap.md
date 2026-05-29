# 项目愿景与路线图

## 1. 项目是什么

**Mini-Coding-Agent**：极简本地编码 Agent，通过 Ollama 调用本地大模型，在指定 Git 工作区内以工具循环完成读代码、搜索、写文件、跑 shell 等任务。

| 属性 | 说明 |
|------|------|
| 当前形态 | 单文件 `mini_coding_agent.py`（约 1178 行） |
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
| P0 | 无 diff 预览、无 checkpoint/回滚、Git 仅启动时快照 | **Phase 1** |
| P1 | 无可观测性（trace、token、耗时） | Phase 2+ |
| P1 | 无 benchmark / 回归任务集 | Phase 2+ |
| P2 | `run_shell` 全权限、无沙箱 | Phase 2+ |
| P2 | 单文件、无插件化 tool/model | 随功能增量拆分 |
| P3 | 仅 Ollama、非流式 | 按需 |

**结论**：第一刀打在**变更治理层**，而非拆包或多模型。

---

## 4. 阶段规划

### Phase 1 — 变更治理（当前）

- unified diff 预览后再审批
- 单次 tool 级 checkpoint + 回滚
- 只读 Git 加深（risky 前刷新 status）
- 保留 `write_file` / `patch_file`，外层包治理逻辑

详见 [`04-phase1-decisions-and-mvp.md`](./04-phase1-decisions-and-mvp.md)、[`05-phase1-implementation-design.md`](./05-phase1-implementation-design.md)。

### Phase 2（草案，未开工）

- 可观测性：步进日志、工具耗时
- 评估：小型回归任务集 + 成功率
- `run_shell` 约束或沙箱调研

### Phase 3+（草案）

- 多模型抽象、流式输出
- 更深 Git（半自动 commit）
- 模块化拆分（按需）

---

## 5. 铁律

1. **主 Agent 与用户意见一致之前，不生成 Phase 1 实现代码。**
2. **不以空重构开场** — 拆文件跟着功能走。
3. **标准库优先** — 新依赖须主 Agent 批准。
4. **新行为必有 pytest** — 用 `FakeModelClient`，不依赖 Ollama。

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
