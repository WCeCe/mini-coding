# 任务单：R4-TOOLS-EXTRACT

## 元信息

- **TASK_ID**: R4-TOOLS-EXTRACT
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: R3-PROMPT-EXTRACT ✅

---

## 目标

将 **工具实现与 run 管道**从 `agent.py` 迁到 **`mini_coding_agent/tools/`**（包结构由子 Agent 设计，须含清晰模块 map）：

- `build_tools` 注册表（或等价）
- `validate_tool`、`tool_example`、`repeated_tool_call`
- `run_tool` / `_invoke_tool_with_hooks` / `_execute_tool_after_validation` 中与工具执行相关的部分（与 governance、plan-first 的边界须在 feedback 说明）
- 各 `tool_*` 实现（list/read/search/shell/delegate/make_plan/load_skill 等）
- `path` / `path_is_within_root` 沙箱

**完成后** `MiniAgent`  primarily：**`ask`、初始化、Hook 注册、模块接线**。

---

## 约束

- 见 [`REFACTOR-OVERVIEW.md`](./REFACTOR-OVERVIEW.md) §3  
- **行为不变** — Phase 1–4 全部能力保留  
- write/patch 仍只走 R2 治理模块，不在 tools 里直写绕开治理  
- **注释尽量保留**；`tool_*` 旁的用户注释随函数迁移  
- 全量 pytest 绿（当前基线以仓库为准，回报写明 passed/skipped 数）  
- 不引入 ToolSpec 大重构（struct §7 后续项）  

---

## 交付物

- `mini_coding_agent/tools/`（新建包）
- `mini_coding_agent/agent.py`（编排器，目标 ~350–450 行）
- `tests/`（import/patch 调整）
- [`feedback/R4-TOOLS-EXTRACT.md`](../feedback/R4-TOOLS-EXTRACT.md) — **须含最终模块 map 与 agent 行数**

---

## 验收标准

- [ ] `agent.py` 显著瘦身；六大组件职责在模块 map 中可指认  
- [ ] 全量 pytest + ruff 通过  
- [ ] Hook、plan-first、skills、delegate depth 行为不变  
- [ ] feedback 含模块 map、注释迁移说明、agent 行数  

---

## 参考资料

- [`struct/refactor-agent.md`](../struct/refactor-agent.md) §2 目标架构
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md)
- R1–R3 feedback

---

*实现路径由子 Agent 自定*
