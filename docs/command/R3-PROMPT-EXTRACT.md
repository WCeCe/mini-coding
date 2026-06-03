# 任务单：R3-PROMPT-EXTRACT

## 元信息

- **TASK_ID**: R3-PROMPT-EXTRACT
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: R2-GOVERNANCE-EXTRACT ✅

---

## 目标

将 **Prompt 形状**相关逻辑迁到 **`mini_coding_agent/prompt.py`**：

- `build_prefix`（含 tools 清单、rules、examples、skill metadata 注入点）
- `memory_text`（含 plan、loaded_skills 等 memory 块）
- `history_text`
- `prompt()` 组装（或等价函数，由子 Agent 设计）

`MiniAgent.ask()` 仍负责调用 prompt 构建并传入 `model_client`。**行为与文案不变**（中文规范见 [`04-user-facing-locale.md`](../struct/04-user-facing-locale.md)）。

---

## 约束

- 见 [`REFACTOR-OVERVIEW.md`](./REFACTOR-OVERVIEW.md) §3  
- prompt 模块可接收 **上下文对象**（tools dict、workspace、memory、skill catalog 等），避免循环 import；具体形状子 Agent 自定  
- **注释整段迁移**；rules/examples 旁的用户注释保留  
- 不迁 `ask` 主循环、不迁 `run_tool`（R4）  
- 全量 pytest 绿  

---

## 交付物

- `mini_coding_agent/prompt.py`（新建）
- `mini_coding_agent/agent.py`（委托 prompt）
- [`feedback/R3-PROMPT-EXTRACT.md`](../feedback/R3-PROMPT-EXTRACT.md)

---

## 验收标准

- [ ] agent 无大段 prefix/memory/history 字符串拼装  
- [ ] `/memory`、prompt 中 plan/skill 块与重构前一致  
- [ ] pytest + ruff 通过  
- [ ] feedback 含注释迁移说明  

---

## 参考资料

- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) §2–§3
- 当前 `agent.py` `build_prefix`、`memory_text`、`history_text`、`prompt`

---

*实现路径由子 Agent 自定*
