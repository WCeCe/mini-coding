# Eval QA 踩坑日志

> 返回索引：[`README.md`](./README.md) · Phase 7 总览：[`struct/phase7.md`](../struct/phase7.md) · Live 产物：[`eval/runs/README.md`](../../eval/runs/README.md)

每次 live eval 发现**根因明确**的失败，追加一条记录，并补 `tests/regression/test_discovered_bugs.py` 回归。能在 L1/L2 复现的 bug **不必**依赖 Ollama。

---

## 条目模板

```markdown
## 轮次 N — {简短标题}

**日期**：YYYY-MM-DD  
**触发**：live eval / 人工 / CI

| 任务/触发 | failure_type | 根因 | 修复摘要 | 回归测试 |
|-----------|--------------|------|----------|----------|
| {task_id} | {type} | {path 或机制} | {what changed} | {TestClassName} |
```

---

## 轮次 0 — GL-5 / 波次 C（历史）

**日期**：2026-06-04 ~ 2026-06-05

| 任务/触发 | failure_type | 根因 | 修复摘要 | 回归 |
|-----------|--------------|------|----------|------|
| off_by_one（改前） | verify 假阳 | verify 有 tests/ 须 pytest | EV-1 对齐 | `TestBug_VerifyPytestNotPycompile` |
| syntaxerror_paren | generate_patch_match | LLM 自填 old_text | → **7.2 系统注入** | `TestBug_PatchOldTextNormalize` → guided |
| nameerror_greet | generate_protocol | JSON 嵌套引号 | protocol 容错 | `TestBug_ProtocolNestedQuotes` |
| eval 不读 session | 报告缺口 | run_eval | 波次 D observability | ✅ |
| locate 永远 ok | 架构盲点 | locate 无 snippet 门槛 | B4 + contract | 部分 ✅ |

---

## 轮次 1 — Phase 7.2 Generate 引导 patch

**日期**：2026-06-08  
**触发**：Generate 专项 8 条 live（[`eval/runs/`](../../eval/runs/README.md)）

| 任务/触发 | failure_type | 根因 | 修复摘要 | 回归 |
|-----------|--------------|------|----------|------|
| off_by_one_sum 等 | old_text 0 匹配 | LLM 抄 snippet 丢缩进 | **7.2** 系统填 old_text | `test_generate_fix_bug_guided_*` |
| 多条 | fallback_open | pipeline fail → open 超时 | **7.2** 取消 open 降级 | `test_pipeline_failure_returns_error_*` |
| pytest 类 | locate 仅 tests 路径 | 无 RIG | **7.2** ensure_rig | `test_run_pipeline_ensures_rig` |
| off_by_one_sum | generate_protocol | 模型返回 ` ``` ` 无 tool | 代码块兜底 | `test_generate_fix_bug_guided_accepts_codeblock_*` |
| syntaxerror_paren | generate_protocol → expect_files | 未闭合 JSON；后缺 `\n` | **7.3** protocol · **7.4** 写盘换行 | `test_protocol_parse_unclosed_*` |
| nameerror_greet | expect_files | f-string 非 `return name` | **7.4** 任务改 tests_only | — |
| no_file_hint_add | verify_pytest | 无 files_hint | **7.3** slots `add(2,3)` | SL-26 |

### 出厂条件（轮次 1）

- [x] Generate 专项 8 条：0/8 → **5/8**（7.2）
- [x] `stage_trace` 写入每次 eval
- [x] live 产物归档至 `eval/runs/`
- [x] 7.3：protocol + no_file_hint locate
- [x] 7.4：写盘 `\n` + nameerror_greet pytest 任务
- [ ] 更新 `eval/baselines/live-qwen2.5-coder-7b.json`

---

## 轮次 2 — （待填写）

**日期**：  
**触发**：

| 任务/触发 | failure_type | 根因 | 修复摘要 | 回归 |
|-----------|--------------|------|----------|------|
