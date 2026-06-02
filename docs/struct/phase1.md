# Phase 1：变更治理

> **状态**：✅ 已完成（2026-05-29）  
> **验收**：`feedback/P1-REVIEW.md` · 测试 27 passed, 1 skipped

---

## 1. 已完成

对 `write_file` / `patch_file` 在工具执行层外包**变更治理**，模型 tool 协议不变：

```
读盘 → 算 proposed content → unified diff → approve(diff)
  → 拒绝：零写盘
  → 批准：checkpoint → atomic_write → 失败则回滚
```

| 交付 | 说明 |
|------|------|
| diff 预览 | 终端 unified diff（`--approval ask`） |
| checkpoint | `.mini-coding-agent/checkpoints/<session>/` |
| 回滚 | 单次 tool；新建失败删文件；外部改文件 → `rollback_skipped` |
| session 审计 | `diff_summary`、`checkpoint_id`、`rolled_back` |
| Git 感知 | 审批前 refresh status，脏树警告（只读，不 commit） |
| `run_shell` | 行为不变 |

**实现位置**（Phase 2 重构后）：`mini_coding_agent/agent.py` 中 `_run_governed_file_tool` 等；工具函数在 `util.py`。

---

## 2. 关键决策（摘要）

| # | 决策 | 选定 |
|---|------|------|
| 1 | 预览 | 终端 diff |
| 2 | 回滚粒度 | 单次 tool |
| 3 | Git | 只读警告 |
| 4 | 工具演进 | 保留 write/patch，执行层包治理 |

---

## 3. 可靠性契约（摘要）

| 场景 | 要求 |
|------|------|
| 拒绝审批 | 磁盘与改前一致 |
| 写盘失败 | 自动回滚 |
| checkpoint 失败 | 不写盘 |
| 外部改文件后回滚 | skip，不静默覆盖 |

**未保证**：`run_shell` 副作用；一次 ask 多步一键撤销。

---

## 4. 评估（相对作品集目标）

**特点**

- 核心差异化：「模型不能静默改库」，有契约 + pytest
- diff 审批 + checkpoint 链路完整，面试可 2 分钟讲清
- 与 mature agent（Aider 类）叙事对齐

**不足**

- 大 diff 终端无分页，体验一般
- `approval_policy=auto` 不展示 diff，审计靠 session
- validate 与治理层双读文件，极端 TOCTOU 未消除
- `tool_write_file`/`tool_patch_file` 直写路径仍存在（run_tool 已 bypass）

---

## 5. 后续可优化（Phase 1 范围内）

| 优先级 | 方向 | 说明 |
|--------|------|------|
| P1 | 清理 dead path | 移除或私有化未被 `run_tool` 调用的直写工具实现 |
| P1 | 大 diff 体验 | 终端截断 +「完整 diff 见 checkpoint 旁文件」可选 |
| P2 | 一次 ask 撤销 | per-ask checkpoint 栈，一键恢复本轮全部文件修改 |
| P2 | `auto` 模式可选 diff 日志 | 不交互但仍写 stderr / 文件供事后查 |
| P3 | 写盘前二次读盘 | 缩小 validate 与 apply 之间的时间窗 |

---

## 6. 面试一句话

> 写文件前先看 diff，批准后才 checkpoint 和原子写盘；拒绝或失败可回滚，session 可审计；run_shell 故意未纳入回滚。

---

*Phase 1 唯一 struct 文档 · 历史细节见 `feedback/P1-*`*
