# 子 Agent 回报：P5-DOCS

## 元信息

- **TASK_ID**: P5-DOCS
- **TASK_TYPE**: DOCS
- **状态**: 完成

---

## 方案摘要

在根 [`README.md`](../../README.md) 新增 **§ Graph Harness (Phase 5)**，与 [`struct/phase5-graph.md`](../struct/phase5-graph.md) 及 P5.1–P5.6 feedback 一致：

- 文首 bullet 增加 Graph Harness (Phase 5)
- **§ Graph Harness (Phase 5)**：五类 intent 表、Gate/流水线、`--harness` / `--gate-log`、`rig build`、open 降级表、harness session 字段、`/reset` 清空、`--plan-first` 互斥说明、MVP vs 5.7+ Future 表、Known limitations
- **§ Interactive Commands**：`/reset` 补充 harness 字段
- **§ Main CLI Flags**：`--harness`、`--gate-log`；RIG 子命令 `rig build`

未改 `mini_coding_agent/` 业务逻辑。

---

## 契约与 Done Definition 自证

| 条目（任务单验收标准） | 是否满足 | 证据 |
|------------------------|----------|------|
| README 有 Graph Harness 专节 | ✅ | § Graph Harness (Phase 5) |
| 五类 intent 表与 struct §5.1 一致 | ✅ | 表内 5 个 `intent_id` + 拓扑摘要 |
| 说明 `--harness`、`--gate-log` | ✅ | § CLI: `--harness` and `--gate-log` |
| 说明 `rig build` | ✅ | § Offline code graph: `rig build` |
| 明确 low/失败 → open | ✅ | § Open fallback 表 |
| Phase 1 治理仍适用 | ✅ | 开篇段落 + generate 节点说明 |
| Future 表 5.7+ | ✅ | § MVP delivered vs future (5.7+) |
| `/reset` 与 harness 字段 | ✅ | § Harness fields + § Interactive Commands |
| plan-first 与 harness 互斥 | ✅ | § `--plan-first` vs Graph Harness |
| feedback 落盘 | ✅ | 本文档 |

---

## 交付物

| 文件 | 变更 |
|------|------|
| `README.md` | 文首 bullet；§ Graph Harness (Phase 5)；`/reset`；CLI flags + `rig build` |
| `docs/feedback/P5-DOCS.md` | 本回报 |

### README 章节对照

| 章节 | 内容 |
|------|------|
| 文首 bullet | Graph Harness、`--harness`、`--gate-log`、`rig build` |
| **Graph Harness (Phase 5)** | 五类 intent、CLI、RIG、open 降级、session 字段、plan-first 互斥、MVP/Future 表、limitations |
| **Interactive Commands** | `/reset` 含 harness 字段 |
| **Main CLI Flags** | `--harness`、`--gate-log`；`rig build` 子命令 |

---

## 验证结果

文档任务，无代码变更。未跑 pytest/ruff（任务单未要求）。

### 自检清单（对照实现）

| 声称 | 实现来源 | 一致 |
|------|----------|------|
| 五类 `intent_id` 封闭 | `harness/types.py` `INTENT_IDS` | ✅ |
| `--harness` 默认 `off` | `cli.py` | ✅ |
| `--gate-log` 可单独观测 | `runner.handle_ask` | ✅ |
| `rig build` → `.mini-coding-agent/rig.db` | `rig/store.py` `default_db_path` | ✅ |
| low/非法/流水线失败 → `ask()` | `runner.py` | ✅ |
| harness session 四字段 | `harness/session_ctx.py` | ✅ |
| `/reset` 清空 harness | `agent.reset()` + `clear_harness_session` | ✅ |
| Gate skill → `load_skill` | `pipeline.run_pipeline` | ✅ |
| 默认 harness off | `cli.py` default | ✅ |

---

## 风险与未解决问题

- README 主体仍为英文，与 skills 目录中文 README 并存；stderr 示例与代码中文文案一致。
- struct / `docs/README.md` 状态板由主 Agent 在 P5-REVIEW 通过后更新（本任务未改 struct）。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**
- **备注**: 主 Agent spot-check README § Graph Harness (Phase 5)：五类 intent 表、open 降级、`--harness`/`--gate-log`、`rig build`、harness session 字段、`/reset`、`--plan-first` 互斥、MVP vs 5.7+ 表均与 `harness/`、`rig/`、`cli.py` 一致。文首 bullet、Interactive Commands、Main CLI Flags 已同步。`struct/README.md` 与 `phase5-graph.md` 状态板已标 **Phase 5 MVP ✅ 结项**。
