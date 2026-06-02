# 子 Agent 回报：P2-DOCS

## 元信息

- **TASK_ID**: P2-DOCS
- **TASK_TYPE**: DOCS
- **状态**: 完成

---

## 方案摘要

在 `README.md` 新增 **Extension & Observability** 小节，说明 Phase 2 工具边界 Hook（`pre_tool` / `post_tool`）、默认 trace、`register_hook` 概念用法、包布局与 Phase 2 已知限制。

同步更新文首 bullet：实现改为 `mini_coding_agent/` 包 + CLI 入口；功能列表增加 hooks。

**Change Governance** 与 Phase 1 **Known limitations** 全文保留；会话路径说明移至新小节 **Sessions and Resume**（原内容未删，仅加标题便于与 Extension 区分）。

未改业务代码、未改 `EXAMPLE.md`（任务单仅要求 README 必须）。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| README 有 Extension & Observability | ✅ | `README.md` § Extension & Observability |
| Hook 是什么、默认 trace、自定义注册（概念级） | ✅ | 同节 What hooks do / Default trace hook / Registering custom hooks |
| CLI / 模块路径因重构已更新 | ✅ | 文首 package 说明；Project layout 表；Basic Usage 仍为 `python mini_coding_agent.py` / `uv run mini-coding-agent` |
| Phase 1 Change Governance 完整 | ✅ | § Change Governance 未删改 |
| Phase 1 Known limitations 完整 | ✅ | § Known limitations (Phase 1) 五项保留 |
| Phase 2 已知限制 | ✅ | § Known limitations (Phase 2) 五项 |
| struct/07 §4.2 README 文档指标 | ✅ | Extension & Observability + 已知限制 |
| 与 reliability 契约一致 | ✅ | 只观察、fail-open、无外部 Hook、不替代 approve |

---

## 交付物

| 文件 | 变更 |
|------|------|
| `README.md` | 文首 bullet；新增 Extension & Observability；Sessions and Resume 标题 |
| `docs/feedback/P2-DOCS.md` | 本回报 |

---

## 验证结果

文档任务，无代码变更。已人工核对：

- Hook 事件名：`pre_tool` / `post_tool`（与 `hooks.py` 一致）
- Session 字段：`tool_trace`、`tool_audit`（与 `trace_hook.py` 一致）
- API：`register_hook`、`enable_trace_hook=False`（与 `agent.py` 一致）
- CLI：`python mini_coding_agent.py`、`uv run mini-coding-agent` 示例保留
- Phase 1 治理路径、审批文案、限制项未改动

---

## 风险与未解决问题

- README 为英文，与仓库现有用户文档风格一致
- 交互式 CLI 未暴露 Hook 开关；文档已说明 Hook 面向嵌入/测试场景

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过** — P2-DOCS 可结项；可派发 P2-REVIEW。
- **备注**:
  - 已核对 `README.md`：§ Extension & Observability 完整；§ Change Governance 与 Phase 1 Known limitations 原样保留；Sessions and Resume 路径说明未删。
  - Hook 描述与实现一致（`pre_tool`/`post_tool`、fail-open、`tool_trace`/`tool_audit`、`register_hook`、`enable_trace_hook=False`）。
  - CLI 示例 `python mini_coding_agent.py` / `uv run mini-coding-agent` 保留；包结构表已更新。
  - 仅文档变更，符合任务单「可以写代码: 否」。
  - 无 Blocker。
