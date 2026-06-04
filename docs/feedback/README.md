# feedback — 子 Agent 回报

本目录存放子 Agent **完成任务后**提交给主 Agent 审阅的文档。主 Agent 据此验收、更新 `struct/` 状态板、决定是否派发下一 `command/`。

---

## 命名规范

```
feedback/<TASK_ID>.md
```

与 `command/<TASK_ID>.md` 一一对应。

---

## 主 Agent 验收流程

1. 对照 `command/<TASK_ID>.md` 的验收标准逐项勾选
2. 检查 scope：是否改了任务单外的文件
3. 实现类：确认 pytest / ruff 输出（或自行复跑）
4. 结论写入主 Agent 对话；必要时更新 `struct/README.md` 状态板
5. 不合格：在原 `feedback/` 文件末尾追加「主 Agent 复审」段，或重新派发修订任务

---

## Phase 5 回报索引

**struct 契约**：[`struct/phase5-graph.md`](../struct/phase5-graph.md)

### 波次 A — Graph MVP（5.1–5.6）

| TASK_ID | 内容 | feedback |
|---------|------|----------|
| P5.1-HARNESS-ENTRY | Gate + Runner + CLI | [`P5.1-HARNESS-ENTRY.md`](./P5.1-HARNESS-ENTRY.md) |
| P5.2-TEMPLATES-PLANNER | 五类模板 + Planner | [`P5.2-TEMPLATES-PLANNER.md`](./P5.2-TEMPLATES-PLANNER.md) |
| P5.3-FIX-BUG-PIPELINE | 节点 + fix_bug E2E | [`P5.3-FIX-BUG-PIPELINE.md`](./P5.3-FIX-BUG-PIPELINE.md) |
| P5.4-RIG | index 离线图谱 | [`P5.4-RIG.md`](./P5.4-RIG.md) |
| P5.5-FIVE-INTENTS | 通用 Executor + 五类 E2E | [`P5.5-FIVE-INTENTS.md`](./P5.5-FIVE-INTENTS.md) |
| P5.6-SESSION | Harness 会话字段 | [`P5.6-SESSION.md`](./P5.6-SESSION.md) |
| P5-DOCS | README § Graph Harness | [`P5-DOCS.md`](./P5-DOCS.md) |
| P5-REVIEW | Phase 5 MVP 总验收 | [`P5-REVIEW.md`](./P5-REVIEW.md) |

### 波次 B — 黄金闭环 / Eval（GL-1–5）

| TASK_ID | 内容 | feedback |
|---------|------|----------|
| GL-1-EVAL-INFRA | eval/tasks.json + run_eval.py | [`GL-1-EVAL-INFRA.md`](./GL-1-EVAL-INFRA.md) |
| GL-2-LOCATE-SNIPPETS | Locate 源码 snippet | [`GL-2-LOCATE-SNIPPETS.md`](./GL-2-LOCATE-SNIPPETS.md) |
| GL-3-VERIFY-ERROR-FORMAT | Verify 错误摘要 | [`GL-3-VERIFY-ERROR-FORMAT.md`](./GL-3-VERIFY-ERROR-FORMAT.md) |
| GL-4-FIX-BUG-SLIM | fix_bug 去 review | [`GL-4-FIX-BUG-SLIM.md`](./GL-4-FIX-BUG-SLIM.md) |
| GL-5-LIVE-EVAL | live Ollama 基线 | [`GL-5-LIVE-EVAL.md`](./GL-5-LIVE-EVAL.md) |
| GL-REVIEW | 黄金闭环总验收 | [`GL-REVIEW.md`](./GL-REVIEW.md) |

---

## 其他阶段回报（历史）

| 阶段 | 代表 TASK_ID |
|------|----------------|
| Phase 1 | P1-CHANGE-GOVERNANCE, P1-DOCS, P1-REVIEW |
| Phase 2 | P2-HOOK-AND-REFACTOR, P2-DOCS, P2-REVIEW, P2.1-* |
| Phase 3 | P3-MAKE-PLAN, P3-DOCS, P3-REVIEW |
| Phase 4 | P4-SKILLS, P4-DOCS, P4-REVIEW |
| 重构 | R1–R4-*, REFACTOR-REVIEW |
| 优化 | OPT-ASK-TIMING, OPT-WAIT-DISPLAY, HOOK-ASK-EVENTS |

完整列表见本目录文件名；未在上表列出的文件仍为有效历史记录。

---

## 空白回报

复制 [`TEMPLATE.md`](./TEMPLATE.md) 为 `feedback/<TASK_ID>.md` 并填写。
