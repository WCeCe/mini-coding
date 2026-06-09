# Phase 8 — 聚焦 fix_bug：叙事对齐 + 评测/CLI 分离 + easy 攻坚

> **状态**：📋 P0 叙事项未执行；**8.1 终判 ✅ · 8.2 P1 ✅（post82 18/19）**  
> **前置**：Phase 7 全子阶段 ✅（7.1–7.4）· post82 live baseline **18/19**  
> **总纲**：[`phase7.md`](./phase7.md) · [`phase8.1.md`](./phase8.1.md) · [`phase8.2.md`](./phase8.2.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md)  
> **正式基线**：[`eval/baselines/live-qwen2.5-coder-7b-post82.json`](../../eval/baselines/live-qwen2.5-coder-7b-post82.json)

---

## 0. Phase 8 是什么

Phase 7 解决了 **「小模型怎么 patch」**（guided patch、protocol 容错、stage_trace）。  
Phase 8 解决 **「项目讲什么故事、代码与证据如何对齐」**：

| Phase 7 问题 | Phase 8 对策 |
|--------------|--------------|
| 代码有五意图，eval 只有 fix_bug | 叙事与 eval 聚焦 fix_bug；五意图模板保留，后续补齐 |
| CLI 与 eval 共用 lock_tests | `HARNESS_LOCK_TESTS` 环境变量分离 |
| 58% 易被误读为「整体能力」 | README 分 tier + failure_type 表 |
| easy 43% 拖累整体印象 | P1 攻坚 expect_files / verify_pytest 类失败 |
| FakeModel 测试与 8B 行为脱节 | P2 live smoke（手动，不进默认 CI） |

**方向代号：1+**

- **主叙事**：本地 8B 的 Python bug 修复闭环（Gate → locate → guided patch → verify → retry）
- **副叙事**：19 任务 eval + stage_trace 作为迭代证据链
- **附录（可选）**：5 任务 Graph vs Open Loop 小对比

---

## 1. 设计哲学（答辩 / README 用）

> 这个项目的核心不是「做一个能修所有 bug 的 agent」，而是 **「用工程约束适配小模型能力的边界」**。
>
> 我们刻意放弃通用性，换来的是：可观测的 trace、可复现的评测、针对 8B 失败模式的精准对策（guided patch、结构化 retry、lock_tests 评测隔离）。
>
> **11/19 不是终点，而是理解失败模式的起点。**

对外一句话定位：

> **Mini Coding Agent — 面向本地 8B 的 Python Bug 自动修复 Harness**

---

## 2. 起点数据（post74 baseline）

**模型**：`qwen2.5-coder:7b` · **模式**：live · **Graph harness** · **无 open fallback**

| 指标 | 数值 | 说明 |
|------|------|------|
| 总体 | **11/19（58%）** | `summary.passed/total` |
| easy | **6/14（43%）** | 失败集中区 |
| medium | **5/5（100%）** | bench / 链路类任务稳定 |

### 2.1 已通过（11）

| task_id | tier | failure_type（pass 侧） |
|---------|------|---------------------------|
| `nameerror_calc` | easy | pipeline_ok |
| `off_by_one_sum` | easy | pipeline_ok |
| `wrong_operator_calc` | easy | outcome_ok |
| `importerror_sqrt` | easy | outcome_ok |
| `missing_return_abs` | easy | outcome_ok |
| `no_file_hint_add` | easy | outcome_ok |
| `bench_retry_off_by_one` | medium | pipeline_ok |
| `bench_decoy_calc_backup` | medium | pipeline_ok |
| `bench_gate_explain_boundary` | medium | pipeline_ok |
| `import_chain_rate` | medium | locate_wrong_file（仍 pass） |
| `logic_median_even` | medium | outcome_ok |

### 2.2 未通过（8）— failure_type 聚合

| failure_type | 数量 | task_id |
|--------------|------|---------|
| **expect_files** | 5 | `syntaxerror_paren`, `wrong_comparison_max`, `syntaxerror_colon`, `nameerror_index`, `empty_body_double` |
| **verify_pytest** | 2 | `nameerror_greet`, `off_by_one_range` |
| **exception** | 1 | `bench_no_rig_search` |

---

## 3. 失败模式表（README / 答辩用 — 表格 B）

> **规则**：表中「状态」列随 P1 进展 **诚实更新**；数据必须可追溯到 baseline JSON + `stage_trace`。

| 失败模式 | 典型任务 | 现象（post74） | 已有对策 | 状态 |
|----------|----------|----------------|----------|------|
| old_text 抄错 / 0-match | phase7.1 live | patch 参数无效 | guided patch（7.2） | ✅ |
| traceback 指 tests、源码在别处 | `off_by_one_sum` | locate 缺源码 | RIG neighbor + ensure_rig | ✅ |
| 无文件 hint | `no_file_hint_add` | slots.files_hint 空 | symbols_hint + search | ✅ |
| **语义修错（grading）** | `syntaxerror_paren` | 8.1 前 verify 过、expect_files 挂 | 8.2 test spec + syntax hint | ✅ post82 |
| **pytest 多轮仍失败** | `nameerror_greet` | 3× generate 后 verify 挂 | 8.2 test spec | ✅ post82 |
| 比较 / logic 修错 | `wrong_comparison_max` | 8.1 前 expect_files 不匹配 | 8.1 pytest 终判 | ✅ post82 |
| **off-by-one / range** | `off_by_one_range` | 3× generate 后 verify 挂 | test spec 不足；模型改错 range | ❌ post82 唯一挂题 |
| locate / infra | `bench_no_rig_search` | exception / timeout | RIG + search 回退 | ❌ |

**P1 主攻簇**：`expect_files`（5/8 fail）— 管线常 OK，**generate 产出语义不符合 expect_files**。

---

## 4. Demo 任务（当前 baseline 已通过）

录屏 / 答辩 **固定三条**，不现场跑失败 task：

| 顺序 | task_id | 展示点 |
|------|---------|--------|
| 1 | `nameerror_calc` | 最小闭环：traceback → patch → py_compile |
| 2 | `off_by_one_sum` | pytest + RIG + guided patch |
| 3 | `bench_retry_off_by_one` | verify 驱动 retry（medium） |

**P1 后可 demo**：`syntaxerror_paren`、`nameerror_greet`（post82 已过）。仍避免 demo：`off_by_one_range`。

Demo 前 **必须** 完成 P0（`HARNESS_LOCK_TESTS` 开关），避免 CLI 锁测试踩坑。

---

## 5. 执行计划

### P0 — 立即（叙事 + 测试基础设施）

**目标**：对外故事与代码行为一致；demo 不被 lock_tests / 测试 bug 反噬。

| # | 任务 | 涉及模块 | 验收标准 |
|---|------|----------|----------|
| P0-1 | `HARNESS_LOCK_TESTS` 环境变量 | `executor.py`、`verify.py`、`verify_rules.py`、`eval/run_eval.py` | CLI 默认 **不** 快照/锁 tests；eval 显式 `=1` |
| P0-2 | 修 inverted skip | `tests/test_eval_runner.py` | Ollama **可用** 时跑 live test；不可用时 skip |
| P0-3 | README 主叙事 | `README.md` | 副标题 fix_bug harness；五意图未维护声明 |
| P0-4 | 分 tier 成功率 | `README.md` | 11/19 · easy 6/14 · medium 5/5 |
| P0-5 | 失败模式表（§3） | `README.md` 或链到本文 | 表格 B，含典型 fail 一行说明 |
| P0-6 | Known Limitations | `README.md` | **不** 教用户改源码；说明 eval vs CLI lock 策略 |

#### P0-1 设计要点

```text
HARNESS_LOCK_TESTS=1  → collect_tests_snapshot + check_tests_snapshot_unchanged（eval 默认）
HARNESS_LOCK_TESTS=0  → 跳过快照比对（CLI 默认）
未设置                 → 建议 CLI 默认 0，eval/run_eval.py 启动时强制设为 1
```

**风险（必读）**：`eval/run_eval.py` 若用 `subprocess` 调 agent，须 `env=os.environ` 传递；子进程内 `handle_ask` 须继承该变量。

#### P0 不做

- 不删 executor / RIG / checkpoint（方向 1+ 保留执行壳）
- 不跑全量 19 live
- 不教用户在 `verify_rules.py` 手改

---

### P1 — 一周内（easy 攻坚）

**目标**：easy **6/14 → ≥8/14**；代码目录与叙事对齐。

| # | 任务 | 说明 |
|---|------|------|
| P1-1 | 攻 `syntaxerror_paren` | 先读 stage_trace → 只改 **一项**（如 generate prompt 强调括号闭合）→ **单任务** live → 再全量 19 |
| P1-2 | 攻 `nameerror_greet` | 同上；关注 verify 错误摘要是否进入 retry prompt |
| P1-3 | 攻 `syntaxerror_colon` | 与 paren 同类，可能共用 generate 改动 |
| P1-4 | ~~模板归档~~ | **不做**：五意图模板均留 `templates/`，后续补齐四类 |
| P1-5 | ~~测试标记~~ | **不做**：`test_harness_five_intents.py` 留在默认 pytest |
| P1-6 | 更新失败模式表 | P1 通过的 task，表中 ❌ → ✅ |
| P1-7 | 新 baseline | `--save-baseline` → 如 `live-qwen2.5-coder-7b-post80.json` |

#### P1 纪律（每改一个 task）

1. **只分析一条** stage_trace（失败节点：generate / verify / locate）
2. **只改一个策略**（一个 PR 意图）
3. **只跑该 task** live（`eval/run_eval.py --task <id> --live`）
4. 通过后再 **全量 19** 回归
5. 同步更新 §3 表格「状态」列

#### P1 任务优先级

| 优先级 | task_id | failure_type | 理由 |
|--------|---------|--------------|------|
| 1 | `syntaxerror_paren` | expect_files | verify 已过，差语义 — 改动面最小 |
| 2 | `nameerror_greet` | verify_pytest | retry 故事完整，答辩常问 |
| 3 | `syntaxerror_colon` | expect_files | 与 paren 同类，可能一批修 |

---

### P2 — 有余力（live smoke）

**目标**：FakeModel 与 8B 之间补一层手动验证，**不进默认 CI**。

| # | 任务 | 说明 |
|---|------|------|
| P2-1 | 目录 `tests/live/` | `@pytest.mark.live` |
| P2-2 | 3 条 smoke | `nameerror_calc`、`off_by_one_sum`、`syntaxerror_paren`（后随 P1 更新预期） |
| P2-3 | 文档 | README：release 前 `pytest -m live` 手动跑 |

**验收**：Ollama 不可用时 skip；可用时对 demo 三条 assert `passed`（或 3 跑 2 过 — 需在测试中注释约定）。

---

### P3 — 可选（Graph vs Open 附录）

**目标**：回答「Graph 比 Open 好在哪里」— **接受 Graph 胜率不更高的结论**。

| # | 任务 | 说明 |
|---|------|------|
| P3-1 | 选 5 任务 | 从 demo + P1 已过的 easy 里选 |
| P3-2 | 双模式跑分 | 同模型、`--harness on` vs `off` |
| P3-3 | 对比维度 | 成功率、步数、token（若可观测）、是否有 stage_trace |
| P3-4 | 写入 README | 「设计反思」一节；Graph 价值 = 可观测 + 可控，未必 = 更高 pass rate |

**时间紧则整包省略**，不阻塞答辩。

---

## 6. 范围边界

### 6.1 保留（active）

| 路径 | 说明 |
|------|------|
| `modes/graph/templates/*.json` | 五类 DAG 模板；eval 现阶段仅 fix_bug |
| `modes/graph/nodes/locate.py` | + generate + verify |
| `modes/graph/executor.py` | 通用 DAG 壳（单意图仍需要） |
| `index/` | RIG；P1 后可做 rig on/off 小统计，不强制删除 |
| `eval/tasks.json` | 19 条均为 `harness_intent: fix_bug` |
| `modes/open/` | 保留作对照，README 不主打 |

### 6.2 五意图（保留，不归档）

五类模板与节点代码均留在主路径；**不做** `experimental/` 物理迁移。当前阶段 eval / 叙事聚焦 fix_bug，其余四类后续补齐 live 与文档。

### 6.3 明确不做（Phase 8）

- 8B 动态规划整张 DAG
- Phase 8 内五意图 live 全量补全（延期到后续阶段）
- 删 executor / 全盘改 Open Loop
- README 裸奔「58%」不分 tier
- Known Limitations 教用户改源码

### 6.4 刻意延期（Future Work）

- RIG 10 任务 × on/off × 3 轮 A/B 表
- checkpoint retry 源码级集成测试
- 8B 动态「模式选择」（非 DAG replan）

---

## 7. 关键承诺清单

| # | 承诺 | 阶段 | 验证方式 |
|---|------|------|----------|
| C1 | lock_tests 有环境变量，CLI 默认不锁 | P0 | 手动改 tests/ 后 CLI pipeline 不 policy_block |
| C2 | README 分 tier，不裸奔 58% | P0 | README 含 easy/medium 表 |
| C3 | 失败模式表为表格 B，可溯源 post74 | P0 | 链到 baseline 文件 |
| C4 | 不教用户改 verify_rules.py | P0 | README 审查 |
| C5 | inverted skip 已修 | P0 | `pytest tests/test_eval_runner.py -m integration` |
| C6 | easy ≥ 8/14 | P1 | 新 baseline summary |
| C7 | 五意图模板在 `templates/` | — | 目录检查 |
| C8 | Demo 三条稳定可录 | P0+P1 | 手动跑通 |

---

## 8. 文件变更索引（规划，非执行清单）

| 阶段 | 文件 |
|------|------|
| P0 | `mini_coding_agent/modes/graph/executor.py` |
| P0 | `mini_coding_agent/modes/graph/nodes/verify.py` |
| P0 | `mini_coding_agent/modes/graph/verify_rules.py` |
| P0 | `eval/run_eval.py` |
| P0 | `tests/test_eval_runner.py` |
| P0 | `tests/test_harness_verify_align.py`（lock 行为随 env 调整） |
| P0 | `README.md` |
| — | 五意图模板保留 `modes/graph/templates/`（不迁 experimental） |
| P1 | `modes/graph/nodes/generate.py`（expect_files 类 prompt） |
| P1 | `eval/baselines/` 新 baseline |
| P2 | `tests/live/test_smoke_fix_bug.py` |
| P2 | `pytest.ini` 或 `pyproject.toml` 注册 `live` marker |

---

## 9. 验收与结项标准

Phase 8 **最低结项**（可答辩）：

- [ ] P0 全部完成（C1–C5）
- [ ] README 与设计哲学（§1）一致
- [ ] Demo 三条录屏素材跑通
- [ ] easy ≥ 8/14 或失败模式表对剩余 fail 有 **stage_trace 级** 解释

Phase 8 **完整结项**（理想）：

- [ ] 上述 + P2 live smoke
- [ ] 新 baseline ≥ post74 总体通过率
- [ ] （可选）P3 对比实验一节

---

## 10. 阅读顺序

1. 本文（Phase 8 总纲）
2. [`phase8.1.md`](./phase8.1.md) — **P0 终判统一（优先执行）**
3. [`phase7.md`](./phase7.md) — 7.x 技术前置
3. [`eval/baselines/README.md`](../../eval/baselines/README.md) — 基线口径
4. post74 JSON — 失败 task 的 `stage_trace` 原文
5. P0 完成后：`README.md` 对外版

---

## 11. 变更日志

| 日期 | 说明 |
|------|------|
| 2026-06-09 | Phase 8 规划文档创建；方向 1+ 与 P0–P3 共识写入；**尚未执行代码** |

---

*phase8.md · 叙事对齐与 fix_bug 聚焦 · 2026-06-09*
