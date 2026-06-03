# 任务单：R1-PROTOCOL-EXTRACT

## 元信息

- **TASK_ID**: R1-PROTOCOL-EXTRACT
- **TASK_TYPE**: IMPLEMENT（纯结构迁移）
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: 无

---

## 目标

将 `MiniAgent` 上的**模型输出协议解析**（`parse`、`parse_xml_tool`、`parse_attrs`、`extract`、`extract_raw`、`retry_notice` 等）迁到 **`mini_coding_agent/protocol.py`**，使 agent 仅调用模块函数。**行为不变**。

---

## 约束

- 见 [`REFACTOR-OVERVIEW.md`](./REFACTOR-OVERVIEW.md) §3  
- **纯函数优先** — 新模块尽量不依赖 `MiniAgent` 实例  
- **`ask()` 与 `run_tool` 语义不变** — 仅 import 路径变化  
- **注释**：原 `parse` 相关注释**整段迁移**到 `protocol.py`；agent 可留一行「见 protocol」；**不得**批量删注释  
- 测试：更新 patch/import 路径；全量 pytest 绿  
- 不碰 governance、prompt、tool 实现（留给 R2–R4）

---

## 交付物

- `mini_coding_agent/protocol.py`（新建）
- `mini_coding_agent/agent.py`（瘦身，委托 protocol）
- `tests/`（若需调整 import/patch）
- [`feedback/R1-PROTOCOL-EXTRACT.md`](../feedback/R1-PROTOCOL-EXTRACT.md)

---

## 验收标准

- [ ] 协议解析逻辑不在 `agent.py` 中重复实现  
- [ ] 全量 pytest + ruff 通过  
- [ ] 无行为变更（parse/retry/final/tool JSON·XML 路径一致）  
- [ ] feedback 含**注释迁移说明**与模块 map  
- [ ] 未改 Phase 1–4 治理/Hook/plan/skill 逻辑  

---

## 参考资料

- [`struct/refactor-agent.md`](../struct/refactor-agent.md)
- [`struct/02-codebase-reference.md`](../struct/02-codebase-reference.md) §5 模型输出格式
- 当前 `agent.py` 中 `parse` 段及静态方法

---

*实现路径由子 Agent 自定*
