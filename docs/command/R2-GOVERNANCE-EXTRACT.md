# 任务单：R2-GOVERNANCE-EXTRACT

## 元信息

- **TASK_ID**: R2-GOVERNANCE-EXTRACT
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: R1-PROTOCOL-EXTRACT ✅

---

## 目标

1. 将 **Phase 1 变更治理**（diff、checkpoint、approve、回滚、`_proposed_file_content` 等）迁到 **`mini_coding_agent/governance.py`**（或子 Agent 命名的等价模块）。  
2. **移除 dead path**：`write_file` / `patch_file` **仅**经治理链；删除或不再注册无用的 `tool_write_file` / `tool_patch_file` 直写路径（用户已确认去掉）。  
3. `agent.run_tool` → 治理的调用关系保持；Hook / plan-first 门控**仍在 agent 或明确文档化的边界**（不绕过 approve）。

---

## 约束

- 见 [`REFACTOR-OVERVIEW.md`](./REFACTOR-OVERVIEW.md) §3  
- **Phase 1 可靠性契约不变** — 见 [`phase1.md`](../struct/phase1.md)  
- dead path 删除时，**仅删除不可达逻辑**；相关注释若仍适用则迁到 governance；若仅描述 dead path 则可删并说明  
- `--plan-first` 门控位置不变（validate 后、治理/approve 前）  
- 全量 pytest 绿；Phase 1 治理用例必须通过  
- 注释迁移说明必填  

---

## 交付物

- `mini_coding_agent/governance.py`（新建）
- `mini_coding_agent/agent.py`（委托治理）
- `tests/`（若有 patch 路径调整）
- [`feedback/R2-GOVERNANCE-EXTRACT.md`](../feedback/R2-GOVERNANCE-EXTRACT.md)

---

## 验收标准

- [ ] 治理逻辑集中在一模块；agent 无大段 diff/checkpoint/rollback 实现  
- [ ] `write_file`/`patch_file` 无 dead `tool_*` 直写注册  
- [ ] Phase 1 治理测试全绿  
- [ ] plan-first / Hook 回归仍绿  
- [ ] feedback 含 dead path 处理说明 + 注释迁移说明  

---

## 参考资料

- [`struct/phase1.md`](../struct/phase1.md)
- [`feedback/P1-CHANGE-GOVERNANCE.md`](../feedback/P1-CHANGE-GOVERNANCE.md)
- 当前 `agent.py` `_run_governed_file_tool`、`approve` 段

---

*实现路径由子 Agent 自定*
