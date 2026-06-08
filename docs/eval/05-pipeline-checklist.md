# 架构逐步验证清单（Phase 0–8）

> 返回索引：[`README.md`](./README.md) · 五层体系：[`02-five-layer-system.md`](./02-five-layer-system.md)

本清单是 eval **必须覆盖**的 fix_bug 黄金路径每一步。列 **L1 / L2 / L3 / L4** 表示该验证点在哪一层实现；✅ 已有、📋 规划、— 不适用。

**图例**：S = 架构步骤编号；验证点 = 具体断言内容。

---

## Phase 0：入口与路由

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 0.1 | `--harness off` 直接 `agent.ask()`，无 Gate stderr | CLI 测 | — | — | — | ✅ |
| 0.2 | `--gate-log` 只记 Gate，不跑 pipeline | `test_harness_gate.py` | — | B3 部分 | — | ✅ |
| 0.3 | `--harness on` 进入 pipeline（fix_bug 消息） | E2E | 契约 | — | live | ✅ |
| 0.4 | eval 脚本 `handle_ask(harness_enabled=True)` 等价 CLI harness on | — | 契约 | — | live | ✅ |

---

## Phase 1：Gate（S1）

**代码**：`mini_coding_agent/modes/graph/gate.py` · `gate_prompt.py` · `runner.py`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 1.1 | 合法 JSON `fix_bug` + `high` → `route=harness_pipeline` | G-01 | arch.gate | — | observability | ✅ L2 |
| 1.2 | `confidence=low` → `route=open`，跳过 pipeline | G-02 | — | — | `gate_low` | ✅ L4 部分 |
| 1.3 | 非 JSON / 畸形响应 → 安全降级 open | G-03 | — | — | — | ✅ gate test |
| 1.4 | unknown intent（如 `add_test`）→ open | gate test | — | — | — | ✅ |
| 1.5 | `session.last_gate` 持久化字段完整 | session test | arch.gate | — | observability | ✅ / 📋 |
| 1.6 | explain 问句不误入 fix_bug DAG | — | — | **B3** | `gate_wrong_intent` | ✅ B3 |
| 1.7 | stderr `[gate] intent_id=… confidence=… route=…` 格式 | gate test | — | — | steps[] | ✅ |

---

## Phase 2：Planner + Slots（S2–S3）

**代码**：`pipeline.py` · `planner.py` · `slots.py` · `templates/fix_bug.json`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 2.1 | `fix_bug.json` 模板：locate→generate→verify + retry max 2 | planner test | 契约 | — | — | ✅ |
| 2.2 | traceback `File "calc.py"` → `files_hint` 含 calc.py | SL-01 | nameerror | — | — | ✅ D1 |
| 2.3 | 消息 `请修复 calc.py` → files_hint | SL-02 | — | — | — | ✅ D1 |
| 2.4 | 无路径 `add(2,3)得-1` → symbols_hint 含 add | SL-15 | no_file_hint | — | — | ✅ D2 |
| 2.5 | 纯 explain 问句 → 无误导 files_hint | SL-16 | — | B3 | — | ✅ D2 |
| 2.6 | 工作区有 `tests/` → `test_command=python -m pytest -q` | SL-05 | off_by_one | — | verify.method | ✅ |
| 2.7 | Gate 返回 skill → load_skill 预加载 | five_intents | — | — | — | ✅ |
| 2.8 | `goal` 截断 ≤300 字符 | planner | — | — | — | ✅ |

---

## Phase 3：Locate（S4）

**代码**：`nodes/locate.py` · `snippet.py` · RIG index

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 3.1 | files_hint → snippet 含 `# calc.py:N` 行号 + 源码 | L-01 | arch.locate | — | — | ✅ L2 / D3 |
| 3.2 | 有 RIG index → `used_rig=True`，snippet 非空 | L-02 | — | — | — | ✅ |
| 3.3 | 无 index.db → search 回退，snippet 非空 | L-03 | — | **B4** | — | ✅ B4 |
| 3.4 | decoy：calc.py + calc_backup.py 只应定位/修改前者 | — | — | **B2** | `locate_wrong_file` | ✅ B2 |
| 3.5 | 跨文件：bug 在 rates.py，failure 表象在 app.py | — | import_chain | **B5** | must_modify | ✅ B5 |
| 3.6 | 无有效 snippet 时 fail（契约任务可选） | — | arch.locate.min | B4 | `locate_no_snippet` | ✅ P2-b |
| 3.7 | locate 节点当前永远 ok=True（已知限制） | — | — | — | — | ✅ P2-b |

---

## Phase 4：Generate（S5）

**代码**：`nodes/generate.py` · `platform/protocol.py`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 4.1 | 必须返回 `kind=tool`（write_file/patch_file） | GN-04 | 契约 | — | `generate_protocol` | ✅ |
| 4.2 | 返回 `<final>` → generate fail | GN-04 | fake final | — | — | ✅ |
| 4.3 | JSON 尾 `}` 多余 → protocol 容错 | GN-02 | — | — | — | ✅ robust test |
| 4.4 | fix_bug old_text 缩进不一致 → normalize | GN-03 | — | — | `generate_patch_match` | ✅ |
| 4.5 | old_text 0 次/多次匹配 → tool 错误 | — | — | — | `generate_patch_match` | ✅ live 已知 |
| 4.6 | 变更经 `run_tool` → governance | E2E | — | — | `generate_governance` | ✅ |
| 4.7 | `must_modify` 文件确实被修改 | — | arch | B5 | files_touched | ✅ |
| 4.8 | retry 时 prompt 含 `last_verify_error` | error_format | B1 | — | generate_attempts | ✅ B1 |

---

## Phase 5：Verify（S6）

**代码**：`nodes/verify.py` · `verify_rules.py`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 5.1 | 有 tests/ → **必须 pytest**，不得 py_compile 假阳 | V-01 | off_by_one | — | `verify_pytest` | ✅ EV-1 |
| 5.2 | generate.path 在 tests/ 下 → fail | V-02 | lock | — | `verify_lock_tests` | ✅ |
| 5.3 | tests/ 快照 vs test_baseline 不一致 → fail | V-02 | lock | — | — | ✅ |
| 5.4 | 无 tests/ → 仅 py_compile 改动 .py | V-03 | nameerror | — | — | ✅ |
| 5.5 | harness verify 与 eval 终判同一 `run_task_verify()` | verify_align | 契约 | — | — | ✅ |
| 5.6 | pytest 超时 60s | — | — | — | — | ✅ 实现存在 |
| 5.7 | 错误修复 compile 过但 pytest fail → verify fail | V-01 | off_by_one | — | — | ✅ |

---

## Phase 6：Retry（S7）

**代码**：`executor.py` · `error_format.py` · `templates/fix_bug.json`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 6.1 | verify fail → 跳回 generate 节点 | E2E | — | **B1** | steps | ✅ B1 |
| 6.2 | 最多 2 次 retry（共 3 次 generate） | R-02 | arch.max_attempts | B1 | generate_attempts | ✅ B1 |
| 6.3 | `format_error_for_model` ≤800 字符 / ≤8 行 | error_format | — | B1 | — | ✅ |
| 6.4 | 第 3 次仍 fail → pipeline fail | R-02 | B1 | — | — | ✅ E2E |
| 6.5 | 两次 patch 不同（不重复同样错误） | — | B1 fake_script | B1 | — | ✅ B1 |

---

## Phase 7：Session + Fallback（S8–S9）

**代码**：`session_ctx.py` · `runner.py`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 7.1 | `session.last_verify` 含 ok/method/summary | session | 契约 | — | observability | ✅ |
| 7.2 | `session.last_files_touched` ≤8 路径 | session | must_modify | — | observability | ✅ |
| 7.3 | `session.harness_last_node` 每节点更新 | session | — | — | observability | ✅ |
| 7.4 | pipeline fail → stderr「降级 open」→ agent.ask | E2E | no_open_fallback | — | `fallback_open` | ✅ |
| 7.5 | `/reset` → `clear_harness_session()` | session | — | — | — | ✅ |
| 7.6 | open 修好不标 pipeline_ok | — | arch | — | pipeline_ok | ✅ P0-a |

---

## Phase 8：终判（S10）

**代码**：`eval/run_eval.py` · `verify_rules.py`

| S | 验证点 | L1 | L2 | L3 | L4 | 状态 |
|---|--------|----|----|----|----|------|
| 8.1 | `grading=exact` → expect_files 字节匹配 | eval_runner | nameerror | — | `expect_files` | ✅ |
| 8.2 | `grading=tests_only` → 仅 verify，不要求 expect | eval_runner | off_by_one | — | — | ✅ |
| 8.3 | lock_tests → setup 中 tests/ 不可变 | verify_align | lock | — | — | ✅ |
| 8.4 | `--save-baseline` / `--compare` 回归检测 | eval_runner | — | — | live | ✅ |
| 8.5 | `passed` = outcome_ok ∧ ¬fallback_open | — | — | — | live | ✅ P0-a |
| 8.6 | `--strict-pipeline` → 还要求 pipeline_ok | — | 契约 | — | CLI | ✅ P0-a |

---

## 覆盖率汇总（当前 vs 目标）

| Phase | 步骤数 | 已有覆盖 | 波次 D 目标 |
|-------|--------|----------|-------------|
| 0 入口 | 4 | 4 | 4 |
| 1 Gate | 7 | 5 | 7 |
| 2 Planner/Slots | 8 | 6 | 8 |
| 3 Locate | 7 | 3 | 7 |
| 4 Generate | 8 | 6 | 8 |
| 5 Verify | 7 | 7 | 7 |
| 6 Retry | 5 | 3 | 5 |
| 7 Session/Fallback | 6 | 4 | 6 |
| 8 终判 | 6 | 4 | 6 |
| **合计** | **58** | **42 (72%)** | **58 (100%)** |

---

## 使用方式

1. **派活**：从 📋 项选 P0/P1 任务，对照 [`10-implementation-roadmap.md`](./10-implementation-roadmap.md)。
2. **验收**：波次 D 结项时本表无 📋 项（或明确标注 defer 至 5.8+）。
3. **新功能**：Graph 新增节点时，必须先在本表增加 Phase/验证点，再写代码。

---

*05-pipeline-checklist.md · 波次 D · 2026-06-05*
