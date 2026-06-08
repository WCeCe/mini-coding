# Phase 7.3 — 大纲（protocol 围栏 + locate 无 hint）

> **状态**：🔄 进行中（**7.3-A ✅** · **7.3-B 部分** · expect_files 待观察）  
> **前置**：7.1 ✅ · 7.2 ✅  
> **总纲**：[`phase7.md`](./phase7.md)

---

## 1. 目标

在 **不扩 pip 依赖** 前提下，提升 live 仍失败的 **Generate / Locate** 路径，目标是把 Generate 专项 8 条从 **5/8 → 7/8+**，并减少全量 19 条中的 `generate_protocol` / `locate_wrong_file`。

| 当前 live 痛点（7.2 后） | failure_type | 任务示例 |
|--------------------------|--------------|----------|
| 模型用 ` ```json ` 包 `<tool>`，外层无 tag | `generate_protocol` | `syntaxerror_paren`, `nameerror_greet` |
| 消息无文件路径，slots 空 | `locate_wrong_file` / verify fail | `no_file_hint_add` |
| 管线 OK 但 grading 内容不符 | `expect_files` | 全量 8/19 中多条 |

---

## 2. 工作包 A — protocol 围栏容错

### 2.1 问题

`platform/protocol.parse()` 要求响应中含 `<tool>…</tool>`。部分模型返回：

````
```json
<tool>{"name":"patch_file",...}</tool>
```
````

或整段 JSON 在围栏内但 **无** `<tool>` 标签 → 当前判为 `retry` / `final`，generate 报 `generate 须返回 tool`。

### 2.2 方案（建议）

| 步骤 | 位置 | 行为 |
|------|------|------|
| 1 | `protocol.parse` 或前置 strip | 若全文匹配 `` ```(?:json)?\s*…\s*``` ``，先剥围栏再 parse |
| 2 | 宽松 tool 提取 | 围栏内纯 JSON `{"name":"patch_file",...}` 无 `<tool>` 包装 → 仍返回 `tool` |
| 3 | generate 兜底 | 保留 7.2 代码块 fallback；不重复造轮子 |

### 2.3 测试

| 类型 | 文件 |
|------|------|
| L1 纯函数 | `tests/test_generate_robust.py` 增 GN-09（json 围栏 + tool） |
| 可选 diagnostic | `tests/diagnostic/test_protocol_fence.py`（Batch 8） |
| Live 验收 | `--task syntaxerror_paren` · `nameerror_greet` |

### 2.4 Done Definition

- [x] 上述两任务 **generate/verify 通过**；failure 降为 `expect_files`（模型输出与任务 exact 不一致）
- [x] `test_protocol_parse_*` / GN-09 全绿

**实现**：`protocol.py` — `_unwrap_markdown_fences`、`_extract_unclosed_json_string`（扫描至 `}}`，容忍 f-string `{name}`）

---

## 3. 工作包 B — `no_file_hint` locate 增强

### 3.1 问题

`no_file_hint_add` 类消息只有自然语言（如「给 `add` 函数补全实现」），`slots.files_hint` 为空 → locate 弱 → generate 无可靠源码上下文。

### 3.2 方案（建议，择一或组合）

| 选项 | 位置 | 说明 |
|------|------|------|
| **B1** 符号从消息抽 | `slots.extract_symbols_hint` | 扩展规则：`` `add` ``、「add 函数」、中文「补全 add」 |
| **B2** goal 驱动 search | `locate.run_locate` | `symbols_hint` 空时从 goal 抽候选标识符再 search |
| **B3** RIG 全库符号模糊 | `index/query.py` | 成本高，MVP 可不做 |

**推荐 MVP**：B1 + 现有 search 回退（与 `no_file_hint_add` eval 对齐）。

### 3.3 测试

| 类型 | 文件 |
|------|------|
| L1 | `tests/diagnostic/test_slots_locate.py` 增 SL-25+ |
| L4 | `--task no_file_hint_add` |

### 3.4 Done Definition

- [ ] `no_file_hint_add` live pass 或至少 locate 产出含 `add.py` snippet
- [ ] D1/D2 门槛仍满足

---

## 4. 工作包 C — 可选（非 MVP）

| 项 | 说明 | 优先级 |
|----|------|--------|
| **shadow workspace** | eval 前复制 setup 到影子目录，减少 RIG/路径污染 | P2 |
| **expect_files 放宽** | 部分任务 exact grading 过严；需与任务设计一起审 | 单独议题 |
| **prompt 示例** | generate prompt 明确禁止 json 围栏 | 随 A 一起做 |

---

## 5. 建议实施顺序

```
7.3-A protocol 围栏（1 会话，纯 platform + 测试）
  ↓
7.3-B slots/locate 无 hint（1 会话）
  ↓
L4 复跑 Generate 8 + 全量 19 → 更新 baselines/post72
  ↓
QA_LOG Round 2 + L5 regression（若发现新坑）
```

---

## 6. 不在 7.3 范围

- 新 pip 依赖、换模型、扩 L2 契约（见 Batch 8）
- Gate 规则大改、第六类意图
- 全面重写 `expect_files` 任务集（可开 7.4）

---

## 7. 相关文档

| 文档 | 用途 |
|------|------|
| [`platform-subsystem.md`](./platform-subsystem.md) §5.3 | protocol 现状 |
| [`graph-subsystem.md`](./graph-subsystem.md) §3.2 | slots 规则 |
| [`eval/runs/README.md`](../../eval/runs/README.md) | Phase 7 跑分表 |
| [`eval/QA_LOG.md`](../eval/QA_LOG.md) | 踩坑记录 |

---

*phase7.3-outline.md · Batch 6 占位 · 2026-06-08*
