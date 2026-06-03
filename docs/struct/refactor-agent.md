# Agent 模块重构（非 Phase · 横切）

> **状态**：✅ **已结项**（REFACTOR-REVIEW 2026-06-02）  
> **验收**：[`feedback/REFACTOR-REVIEW.md`](../feedback/REFACTOR-REVIEW.md) · [`02-codebase-reference.md`](./02-codebase-reference.md)  
> **性质**：**不属于** phase1–4 功能阶段；在功能稳定后整理 `MiniAgent` 边界与模块 map。  
> **策略**：R1→R4 分四步 + REVIEW；行为不变；66 passed, 1 skipped。

---

## 1.0 结项摘要 ✅

| 项 | 结果 |
|----|------|
| `agent.py` | ~337 行（编排器） |
| 新模块 | `protocol` · `governance` · `prompt` · `tools/` |
| dead path | write/patch 仅治理链 |
| 测试 | 66 passed, 1 skipped |
| 文档 | `02-codebase-reference` 已更新 |

---

## 1. 为什么要做（背景）

| 问题 | 说明 |
|------|------|
| `agent.py` 过大 | ~1000+ 行，上帝类 |
| 职责混杂 | 协议解析、治理、prompt、工具实现、主循环全在一处 |
| 真实冗余 | `write_file`/`patch_file` 经治理链，`tool_write_file`/`tool_patch_file` 为 **dead path** |
| 元数据重复 | `build_tools` + `validate_tool` + `tool_example` 三处维护 |

**目标**：`MiniAgent` 只做 **编排**（`ask`、组装依赖、委托子模块）；其余按 [`02-codebase-reference.md`](./02-codebase-reference.md) 六大组件下沉。

---

## 2. 目标架构（R4 完成后）

```
mini_coding_agent/
├── agent.py           # 编排：ask、run_tool 入口、模块接线（目标 ~350–450 行）
├── protocol.py        # parse / XML / retry（纯函数，R1）
├── governance.py      # diff、checkpoint、approve、回滚（R2）
├── prompt.py          # build_prefix、memory_text、history_text（R3）
├── tools/             # 工具实现与 runtime（R4）
│   ├── __init__.py
│   ├── runtime.py     # validate、run 管道（可选，由子 Agent 定）
│   └── ...            # list/read/search/shell 等
├── planning.py        # 已有
├── skills.py          # 已有
├── hooks/             # 已有
└── ...
```

**不变**：Phase 1 治理语义、Phase 2 Hook 契约、Phase 3 plan-first、Phase 4 skills；模型 tool 协议；session 形状（除非子 Agent 证明必须微调且回报说明）。

---

## 3. 拆分顺序与 TASK_ID

| 步 | TASK_ID | 产出 | 依赖 |
|----|---------|------|------|
| R1 | R1-PROTOCOL-EXTRACT | `protocol.py` | — ✅ |
| R2 | R2-GOVERNANCE-EXTRACT | `governance.py` + dead path | R1 ✅ · **R2 ✅** |
| R3 | R3-PROMPT-EXTRACT | `prompt.py` | R2 ✅ · **R3 ✅** |
| R4 | R4-TOOLS-EXTRACT | `tools/` | R3 ✅ · **R4 ✅** |
| — | REFACTOR-REVIEW | 02 更新 + 总验收 | R4 ✅ · **REVIEW ✅** |

**建议**：一步一 PR / 一 feedback；不跨步合 PR。

---

## 4. Done Definition（整体）

| # | 交付 | 要求 |
|---|------|------|
| 1 | 模块边界 | R1–R4 模块存在；`agent.py` 行数显著下降（约 ≤450 行，可浮动） |
| 2 | 行为不变 | 全量 pytest 仍绿；无新 pip 依赖 |
| 3 | dead path | `write_file`/`patch_file` 仅走治理链；无未使用的 `tool_write_file`/`tool_patch_file` 注册 |
| 4 | 注释 | **用户注释尽量保留**；迁代码时注释随块迁移；仅当逻辑整段删除才可删对应注释 |
| 5 | 测试 | 可补充 import 路径测试；不删既有行为覆盖 |
| 6 | 文档 | `REFACTOR-REVIEW` 后更新 `02-codebase-reference.md` 模块 map |

---

## 5. 注释铁律（用户明确要求 · 高于一般精简）

1. **不得**为「文件变短」批量删注释。  
2. 代码块迁到新文件时，**原注释一起迁**（可改文件名/符号引用，勿静默丢段）。  
3. 允许**新增**模块头、边界说明注释。  
4. 仅当整段逻辑删除（如 dead path 整函数）时，才可删除该函数上的注释。  
5. 回报须含 **注释迁移说明**（迁了哪些块、删了哪些及理由）。

---

## 6. 明确不做

- 改 tool JSON/XML 协议、改 Phase 1–4 产品行为  
- 引入 DI 框架、过度抽象基类  
- 顺手做 benchmark、ToolSpec 大统一（可记 refactor-agent §7 后续）  
- 与 Phase 4 新功能混在同一 TASK  

---

## 7. 后续可选（本次不派活）

- `ToolSpec` 一处定义 schema + validate + example  
- `validate_tool` 与工具实现 colocate  
- 进一步瘦 `agent.__init__`（factory / builder）

---

*非 Phase 文档 · command 见 `REFACTOR-OVERVIEW.md`*
