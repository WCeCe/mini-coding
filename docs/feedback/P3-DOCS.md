# 子 Agent 回报：P3-DOCS

## 元信息

- **TASK_ID**: P3-DOCS
- **TASK_TYPE**: DOCS
- **状态**: 完成

---

## 方案摘要

在根 `README.md` 补充 **Phase 3 首项**用户说明，与 [`feedback/P3-MAKE-PLAN.md`](P3-MAKE-PLAN.md)、[`struct/phase3.md`](../struct/phase3.md) 一致：

- 文首功能 bullet 增加 task planning
- 新增 **§ Task Planning (Phase 3)**：`make_plan` 用途/参数/JSON 形状、`delegate` 分工、session `memory.plan`、`/memory`、Known limitations
- **§ Interactive Commands**：`/memory` 补充 plan 摘要
- **§ Main CLI Flags**：`--plan-first` 说明
- 示例命令（one-shot 与 REPL）

未改 `mini_coding_agent/`、未展开 benchmark 或后续未派活项。

---

## 契约与 Done Definition 自证

| 条目（任务单验收标准） | 是否满足 | 证据 |
|------------------------|----------|------|
| README 含 `make_plan`（何时用、参数、输出形状摘要） | ✅ | § Task Planning → Tool: `make_plan`、Plan JSON shape |
| README 含 `--plan-first` 与示例命令 | ✅ | 同节 `--plan-first` + 两条 `uv run` 示例 |
| README 提及 `/memory` 可查看 plan 摘要 | ✅ | § Plan in session memory；§ Interactive Commands `/memory` |
| 无与实现不符的声称 | ✅ | 见下方自检（对照 P3-MAKE-PLAN） |
| feedback 落盘 | ✅ | 本文档 |

| struct/phase3.md §3 #9 文档 | ✅ | README 简述工具与 `--plan-first` |

---

## 交付物

| 文件 | 变更 |
|------|------|
| `README.md` | 文首 bullet；§ Task Planning (Phase 3)；`/memory`；`--plan-first` flag |
| `docs/feedback/P3-DOCS.md` | 本回报 |

### README 章节对照

| 章节 | 新增/更新内容 |
|------|----------------|
| 文首 bullet 列表 | `make_plan` / `--plan-first` (Phase 3) |
| **Task Planning (Phase 3)** | 新建：`delegate` vs `make_plan`、工具表、JSON 摘要、memory.plan、`/memory`、`--plan-first`、limitations |
| **Interactive Commands** | `/memory` 含 plan summary |
| **Main CLI Flags** | `--plan-first` 一行说明 |

---

## 验证结果

文档任务，无代码变更。未跑 pytest/ruff（任务单未要求）。

### 自检清单（对照实现）

| 声称 | 实现来源 | 一致 |
|------|----------|------|
| `make_plan`：`goal` 必填、`context` 可选 | `agent.build_tools` schema | ✅ |
| `risky: False`，无 approve | `risky: False` | ✅ |
| 单次 complete，无内部 tool 循环 | `tool_make_plan` | ✅ |
| JSON：`goal`、`steps[]`（id/title/acceptance）、`assumptions`、`out_of_scope` | `planning.validate_plan` | ✅ |
| 最多 12 步 | `PLAN_MAX_STEPS = 12` | ✅ |
| 失败不写 `memory.plan` | `tool_make_plan` except 分支 | ✅ |
| 成功写 `memory.plan` | `session["memory"]["plan"]` | ✅ |
| `/memory` 显示 plan 摘要 | `memory_text()` `- plan:` 块 | ✅ |
| `--plan-first` 约束 write/patch/shell，每轮 ask 重置 | `plan_first` + `_ask_plan_satisfied` | ✅ |
| 不写 plan 文件、无 auto-dispatch | P3-MAKE-PLAN 明确未做 | ✅ |
| `delegate` = 只读子 Agent；`make_plan` = 单次规划 | `tool_delegate` vs `tool_make_plan` | ✅ |

---

## 风险与未解决问题

- README 为英文，与仓库现有风格一致
- `EXAMPLE.md` 未改（任务单仅要求 README）
- Phase 3 后续项（规划与执行衔接、shell 阻断） intentionally 未写

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: ✅ **通过**（2026-06-02）
- **备注**: README § Task Planning (Phase 3) 与实现一致；五条验收标准均满足。struct §3 #9 文档项闭环。
