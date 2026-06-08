# Phase 7.2 — 引导 patch（系统 old_text + LLM new_text）

> **状态**：✅ 已实现  
> **前置**：[`phase7.1-generate-fix-bug.md`](./phase7.1-generate-fix-bug.md)  
> **总览**：[`phase7.md`](./phase7.md)

---

## 1. 问题

Phase 7.1 后 live 仍大量失败在 **Generate**：

- 模型从 locate snippet **抄写 `old_text`** 时常丢缩进 → `old_text 0 匹配`
- 模型先改 `tests/`（7.1 写前已拦，但浪费 retry）

根因：**复制与推理混在一项任务里**，小模型不擅长逐字抄源码。

---

## 2. 方案（B：KWCode 思路的务实子集）

**fix_bug 且能定位到非 `tests/` 源码文件时：**

1. 系统从磁盘读取 `old_text`（≤120 行整文件，否则用 locate snippet 唯一片段）
2. Prompt 展示「待替换原文」，要求 LLM **只输出 `new_text`**
3. `_apply_fix_bug_guided_patch` 组装完整 `patch_file` 参数
4. LLM 若只返回 ` ``` ` 代码块（无 `<tool>`）→ `_try_guided_codeblock_fallback` 提取为 `new_text`

**非 fix_bug**（refactor 等）仍用旧协议（LLM 自填 `old_text` + `new_text`）。

---

## 3. 实现要点

| 模块 | 变更 |
|------|------|
| `nodes/generate.py` | `_resolve_fix_bug_patch_target`、`_apply_fix_bug_guided_patch`、引导 prompt、代码块兜底 |
| `platform/protocol.py` | `patch_file` 允许仅 `path` + `new_text` |
| `index/build.py` | `ensure_rig`（pipeline 入口） |
| `runner.py` | 取消 pipeline 失败 → open |
| `harness_trace.py` | gate / rig / slots / locate / generate / verify 追踪 |
| `eval/run_eval.py` | `observability.stage_trace`、`-o` 写报告 |

---

## 4. Live 验证

| 运行 | 结果 | 文件 |
|------|------|------|
| off_by_one_sum 单条 | **pass** ~29s | [`eval/runs/live/2026-06-08_phase72-off_by_one_sum-pass.json`](../../eval/runs/live/2026-06-08_phase72-off_by_one_sum-pass.json) |
| Generate 专项 7 条 | **4/7** | [`eval/runs/live/2026-06-08_phase72-generate-7tasks.json`](../../eval/runs/live/2026-06-08_phase72-generate-7tasks.json) |

仍失败 3 条：`syntaxerror_paren`、`nameerror_greet`（` ```json ` 包 `<tool>`）、`no_file_hint_add`（无文件 hint → locate 弱）。

---

## 5. 测试

```bash
python -m pytest tests/test_generate_robust.py tests/test_harness_trace.py \
                 tests/test_harness_fix_bug_e2e.py tests/test_rig.py -q
```

---

## 6. 7.3 建议

| 项 | 说明 |
|----|------|
| ` ```json ` + `<tool>` 解析 | 修 syntaxerror_paren / nameerror_greet |
| slots 从 `tests/...::test_foo` 提 symbol | 修 no_file_hint_add |
| 保存正式基线 | `--save-baseline eval/baselines/live-qwen2.5-coder-7b.json` |

---

*phase7.2-guided-patch.md · 2026-06-08*
