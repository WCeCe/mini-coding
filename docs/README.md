# 项目文档索引



本仓库文档按**职责**分为四个目录，避免单文件无限膨胀。主 Agent（战略对话窗口）维护 `struct` 与 `command`；用户维护 `my_research`；子 Agent 产出写入 `feedback`。



---



## 目录说明



| 目录 | 维护者 | 内容 | 何时更新 |

|------|--------|------|----------|

| [`struct/`](./struct/) | **主 Agent** | 构想、架构总览、阶段记录、中文规范 | 战略/阶段变化时 |

| [`command/`](./command/) | **主 Agent** | **目标级**任务（历史派活归档） | 一般不扩写 |

| [`feedback/`](./feedback/) | **子 Agent** | 任务回报（历史归档） | 一般不扩写 |

| [`my_research/`](./my_research/) | **用户** | 调研笔记 | 用户维护 |

| [`eval/`](./eval/) | 规格 + 操作 | 五层 eval 设计（`docs/eval/`）与跑分手册（`eval/`） | eval 变更时 |



---



## 协作工作流



```

主 Agent 更新 struct（构想 / 架构 / 阶段）

        │

        ├─► 用户调研 → my_research/

        │

        ├─► （历史）command/ → feedback/

        │

        ▼

当前迭代：直接改 struct/phase*、eval/、代码 + QA_LOG

```



---



## 子 Agent / 新人快速入口



1. [`struct/ARCHITECTURE.md`](./struct/ARCHITECTURE.md) — **系统总览**（30 分钟看懂）

2. [`struct/phase7.md`](./struct/phase7.md) — **当前代码主线**（Generate 7.1–7.3）

3. [`struct/README.md`](./struct/README.md) — struct 阅读顺序与状态板

4. [`eval/README.md`](../eval/README.md) — 怎么跑 L1–L5 / live eval



---



## 当前阶段（摘要）



| 项目 | 状态 |

|------|------|

| Phase 1–5 | ✅ |

| **架构文档 Batch 0–6** | ✅ [`project-architecture-plan.md`](./struct/project-architecture-plan.md) |

| **Phase 7.1 / 7.2** | ✅ 引导 patch · stage_trace · 无 open 降级 |

| **Phase 7.3** | 📋 [`phase7.3-outline.md`](./struct/phase7.3-outline.md) |

| Eval 五层 L1–L5 | ✅ 文档 + CI 基建 · L4 手动 |

| Live 全量 19（7.2 后） | **8/19** · [`eval/baselines/`](../eval/baselines/README.md) |

| Generate 专项 8 条 | **5/8** · [`eval/runs/README.md`](../eval/runs/README.md) |



---



## 文档地图（精简）



| 我想… | 去看 |

|--------|------|

| **系统总览 / 端到端图** | [`struct/ARCHITECTURE.md`](./struct/ARCHITECTURE.md) |

| **Platform 治理 / protocol** | [`struct/platform-subsystem.md`](./struct/platform-subsystem.md) |

| **Graph 节点 / stage_trace** | [`struct/graph-subsystem.md`](./struct/graph-subsystem.md) |

| **模块速查** | [`struct/02-codebase-reference.md`](./struct/02-codebase-reference.md) |

| **Phase 7 与 7.3 计划** | [`struct/phase7.md`](./struct/phase7.md) · [`phase7.3-outline.md`](./struct/phase7.3-outline.md) |

| **架构整理分批计划** | [`struct/project-architecture-plan.md`](./struct/project-architecture-plan.md) |

| Eval 设计规格 | [`eval/README.md`](./eval/README.md)（`docs/eval/`） |

| 跑 live / 基线对比 | [`eval/README.md`](../eval/README.md) · [`eval/runs/`](../eval/runs/README.md) |

| L2 vs L4 任务划分 | [`eval/L4-ONLY-DECISION.md`](../eval/L4-ONLY-DECISION.md) |

| 踩坑记录 | [`eval/QA_LOG.md`](./eval/QA_LOG.md) |

| 历史派活 | [`command/README.md`](./command/README.md)（只读） |



---



## 代码与使用说明



- 运行与安装：[`../README.md`](../README.md)

- Agent 重构：✅ [`refactor-agent`](./struct/refactor-agent.md)

- 源代码：[`../mini_coding_agent/`](../mini_coding_agent/)



---



*文档体系 v8 · Phase 7.3 规划 · 架构 Batch 0–6 完成 · 2026-06-08*

