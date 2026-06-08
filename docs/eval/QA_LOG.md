# Eval QA 踩坑日志

> 返回索引：[`README.md`](./README.md) · L5 流程：[`02-five-layer-system.md`](./02-five-layer-system.md) §6

每次 live eval 或人工测试发现**根因明确**的失败，追加一条记录，并补 `tests/regression/test_discovered_bugs.py` 回归 class。能在 L1/L2 复现的 bug **不必**依赖 Ollama。

---

## 条目模板

```markdown
## 轮次 N — {简短标题}

**日期**：YYYY-MM-DD  
**触发**：live eval / 人工 / CI / code review

| 任务/触发 | failure_type | 根因文件:行 | 修复摘要 | 回归测试 |
|-----------|--------------|-------------|----------|----------|
| {task_id} | {type} | {path}:{line} | {what changed} | {TestClassName} |

### 出厂条件（本轮）

- [ ] L2 契约全绿
- [ ] 本轮新 bug 均有 regression class
- [ ] live 基线对比无意外 regression（或已更新基线并说明）
```

---

## 轮次 0 — GL-5 / 波次 C 已知问题（历史沉淀）

**日期**：2026-06-04 ~ 2026-06-05  
**触发**：GL-5 live eval + EV 波次 C 审计

| 任务/触发 | failure_type | 根因文件:行 | 修复摘要 | 回归测试 |
|-----------|--------------|-------------|----------|----------|
| off_by_one_sum（改前） | verify 假阳 | `nodes/verify.py` | harness 有 tests/ 时必须 pytest，不能仅 py_compile | `TestBug_VerifyPytestNotPycompile` |
| syntaxerror_paren live | generate_patch_match | `nodes/generate.py` | old_text 0 匹配；EV-3 normalize | `TestBug_PatchOldTextNormalize` |
| nameerror_greet live | generate_protocol | `platform/protocol.py` | 嵌套引号/尾 `}` 容错 | `TestBug_ProtocolNestedQuotes` |
| eval `--fake` 反推 | 设计缺陷 | `eval/run_eval.py`（已移除） | 5/5 从 expect 反推，测接线非智能；改 L2 契约 | `test_eval_contract.py`（规划） |
| eval 不读 session | 报告缺口 | `eval/run_eval.py` | 终判不看 last_gate/last_verify | 波次 D P0-a |
| locate 永远 ok | 架构盲点 | `nodes/locate.py` | 无 snippet 仍 ok=True | 波次 D P2-b + B4 |

### 出厂条件（轮次 0）

- [x] EV-1 verify 对齐（off_by_one 类）
- [x] EV-3 generate/protocol pytest
- [x] L2 契约替代 `--fake`（波次 D P0-b）
- [x] session observability（波次 D P0-a）
- [x] discovered_bugs regression 模块（波次 D P2-a）

---

## 轮次 1 — （待填写）

**日期**：  
**触发**：

| 任务/触发 | failure_type | 根因文件:行 | 修复摘要 | 回归测试 |
|-----------|--------------|-------------|----------|----------|

### 出厂条件（本轮）

- [ ] L2 契约全绿
- [ ] 本轮新 bug 均有 regression class
- [ ] live 基线对比无意外 regression

---

## Regression 测试命名约定

```
tests/regression/test_discovered_bugs.py

class TestBug_20260605_OffByOneVerifyAlign:
    \"\"\"QA_LOG 轮次 0 · off_by_one harness py_compile 假阳\"\"\"
    ...
```

- 类名：`TestBug_{日期}_{简短描述}`
- 每个 class 对应 QA_LOG 一行
- 测试体应能在 **FakeModel / 纯函数** 层复现

---

## Live 基线冻结表

| 环境 | 模型 | passed | outcome_ok | 日期 | 备注 |
|------|------|--------|------------|------|------|
| Windows | qwen2.5-coder:7b | **2/5** | — | GL-5 | 原 5 条 easy |
| — | — | —/15 | — | — | 15 条全量待跑 |

**更新规则**：全量 live 后更新此表；禁止只报 L2 通过率。

---

*QA_LOG.md · 波次 D · 2026-06-05*
