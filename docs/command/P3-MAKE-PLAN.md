# 任务单：P3-MAKE-PLAN

## 元信息

- **TASK_ID**: P3-MAKE-PLAN
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: Phase 1 ✅ · Phase 2 ✅

---

## 目标

交付 **任务规划工具** `make_plan`，使 Mini-Coding-Agent 能将用户的复杂任务拆分为**任务级**步骤（含 acceptance），并在 session 中持久可见；支持 CLI **`--plan-first`** 强制「先规划再执行 risky 工具」。

达到 [`struct/phase3.md`](../struct/phase3.md) §3 Done Definition。

---

## 约束（必须遵守）

- 见 [`PHASE3-OVERVIEW.md`](./PHASE3-OVERVIEW.md) §3 工程规范
- **`make_plan` 与 `delegate` 分工**：`delegate` = 只读调查子 Agent（多步 tool）；`make_plan` = **单次**规划模型调用，**无**内部 tool 循环
- **`risky: False`** — 不触发 approve；不 write/patch/shell
- **结构化输出** — 工具返回须含可机器解析的 plan JSON（字段见 struct §3）；非法 JSON 须明确失败
- **Session** — 成功 plan 写入 `session["memory"]["plan"]`；`memory_text()` 须展示 plan 摘要
- **Prompt** — 在 `build_prefix` 增加规则：多文件改动、需求含糊、或用户要求规划时，鼓励先 `read_file`/`search` 再 `make_plan`
- **`--plan-first`** — CLI 旗标传入 Agent；该次 `ask` 在首次 **risky** tool（`write_file` / `patch_file` / `run_shell`）前须已成功 `make_plan`；enforcement 方式自定，须在 feedback 说明
- **不自动编排** — 不实现按 plan 逐步 auto-dispatch、不写默认 plan 文件
- **Phase 1/2 契约不变** — 治理、Hook observe-only、fail-open
- **保留用户注释** + **新增代码带注释**（铁律 §7）

---

## 交付物

1. 代码：`mini_coding_agent/`（含 `make_plan` 工具、CLI、`memory` 扩展）、`tests/`
2. 回报：[`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md)，须包含：
   - **方案摘要**（工具 schema、plan JSON 形状、planning prompt 要点、`--plan-first` enforcement、与 delegate 对比）
   - **契约对照表**（对照 struct §4）
   - **Done Definition 自证**（逐条 §3）
   - **Phase 1/2 回归说明**
   - `pytest -q` 与 `ruff check .` 输出

---

## 验收标准

- [ ] `make_plan(goal, context?)` 注册为 safe tool；单次模型调用产出结构化 plan
- [ ] plan JSON 含 `goal`、`steps[]`（id、title、acceptance）、`assumptions`、`out_of_scope`；步数有合理上限
- [ ] 成功 plan 写入 `session["memory"]["plan"]`；`/memory` 与 prompt 中可见
- [ ] `--plan-first`：未 plan 时调用 risky tool 被拒绝并提示；关闭时行为与 Phase 2 一致
- [ ] pytest 覆盖解析、校验、memory、CLI gate；使用 `FakeModelClient`
- [ ] Phase 1/2 全量 pytest 仍绿；`ruff check .` 通过
- [ ] feedback 含方案摘要与自证，无 scope 蔓延（无 benchmark、无 auto-orchestrator）

---

## 参考资料

- [`struct/phase3.md`](../struct/phase3.md) — Done Definition · 可靠性契约
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) — 工具链、`delegate`、`memory_text`
- [`struct/phase2.md`](../struct/phase2.md) — Hook 契约
- [`mini_coding_agent/agent.py`](../../mini_coding_agent/agent.py) — `build_tools`、`tool_delegate`、`ask`
- [`mini_coding_agent/cli.py`](../../mini_coding_agent/cli.py) — CLI 旗标模式

---

*实现路径由子 Agent 自定*
