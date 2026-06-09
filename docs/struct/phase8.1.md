# Phase 8.1 — Eval 终判统一（消灭双轨验证）

> **状态**：✅ 已实现（`46 passed`：test_eval_runner + test_harness_verify_align + test_eval_contract）  
> **前置**：[`phase8.md`](./phase8.md) · post74 baseline **11/19**  
> **下一档**：Phase 8.1 结项后进入 Phase 8 P1（generate 攻坚）

---

## 0. 本阶段只解决一件事

**管线 verify 与 eval 终判必须是同一套标准。**

post74 铁证：`syntaxerror_paren` 管线 `last_verify.ok=true`（py_compile），eval 判 `expect_files` 失败。  
8 道失败里 **5 道** 属于此类——不是模型不会修，是**阅卷分裂**。

本阶段 **不做**：改 generate prompt、跑全量 live 19、README 大改（留给 Phase 8 P0 叙事项）。

---

## 1. 问题定义（负责、不糊弄）

### 1.1 双轨验证

| 轨道 | 代码位置 | post74 行为 |
|------|----------|-------------|
| **管线 verify** | `nodes/verify.py` | 有 `tests/` → pytest；否则 → **py_compile** |
| **eval 终判** | `run_eval.py` → `check_task_grading` | `grading: exact` → **先比 expect_files 字符串**，再 verify |

两轨独立 → 管线可宣布成功而 eval 失败；retry 不会在 eval 挂掉时触发。

### 1.2 验证过弱

8 道题仅 `py_compile`：只证明「能解析」，不证明「bug 修好」。  
与 SWE-bench / KWCode 核心差距：**应用测试判行为，不用字符串对答案**。

### 1.3 本阶段边界

| 在本阶段修 | 不在本阶段修 |
|-----------|-------------|
| 统一终判函数 | `nameerror_greet` generate 读不懂测试（P1） |
| 8 道无测试题补 pytest | 全量 live 重跑 baseline |
| `HARNESS_LOCK_TESTS` CLI/eval 分离 | README 叙事表（Phase 8 P0） |
| 修 inverted live test skip | ReAct / Graph vs Open |

---

## 2. 目标状态（结项标准）

### E1 — 单一终判

```text
live 通过 ⟺ lock_tests OK ∧ pytest 全绿
（verify: none 的 gate 边界题除外）
```

- `check_task_grading` **不再**读取 `expect_files`
- `grading` 统一为 `tests_only`（`exact` 视为遗留别名，映射到 `tests_only`）

### E2 — 管线与 eval 共用 `run_workspace_verify()`

- `verify_rules.run_workspace_verify()`：harness + eval 唯一实现
- `nodes/verify.py` 薄封装调用上述函数

### E3 — 19 题中 fix_bug 题均有行为测试

原 8 道 `verify: py_compile` 题补 `tests/test_*.py`，改为 `verify: pytest` + `lock_tests: true`。

### E4 — lock_tests 环境变量

```text
HARNESS_LOCK_TESTS=1  → eval 默认（run_eval.py 启动时 setdefault）
HARNESS_LOCK_TESTS=0  → CLI 默认（不快照、不拦改 tests）
```

### E5 — 测试回归

- `pytest tests/test_eval_runner.py tests/test_harness_verify_align.py tests/test_eval_contract.py` 全绿
- 新增：`test_semantic_fix_passes_without_expect_files`（paren 类语义对、字符串不同仍过）

---

## 3. 任务清单变更（8 题补测试）

| task_id | 新增测试 | 断言要点 |
|---------|----------|----------|
| `nameerror_calc` | `tests/test_calc.py` | `add(2,3)==5` |
| `syntaxerror_paren` | `tests/test_calc.py` | `add(1,2)==3` |
| `wrong_operator_calc` | `tests/test_calc.py` | `add(2,3)==5` |
| `wrong_comparison_max` | `tests/test_maximum.py` | `maximum(5,3)==5` |
| `syntaxerror_colon` | `tests/test_adder.py` | `add(2,3)==5` |
| `nameerror_index` | `tests/test_first.py` | `first([10,20])==10` |
| `empty_body_double` | `tests/test_double.py` | `double(4)==8` |
| `bench_no_rig_search` | `tests/test_helper.py` | `mul(3,4)==12` |

`expect_files` **保留在 JSON 内作人工对照**，live 终判**不读取**。

---

## 4. 代码变更索引

| 文件 | 变更 |
|------|------|
| `verify_rules.py` | `lock_tests_enabled()`、`run_workspace_verify()` |
| `nodes/verify.py` | 调用 `run_workspace_verify`；lock 受 env 控制 |
| `executor.py` | 仅 lock 开启时采集 `test_baseline` |
| `run_eval.py` | 去掉 expect_files 终判；`ensure_eval_lock_tests_env()` |
| `eval/tasks.json` | 8 题补 tests；grading/verify 统一 |
| `tests/test_eval_runner.py` | 修 inverted skip；更新 grading 测试 |
| `tests/test_harness_verify_align.py` | lock env 行为 |

---

## 5. 诚实预期（不夸大）

| 指标 | 预期 |
|------|------|
| `expect_files` failure_type | **归零**（终判不再产生） |
| 总通过率 | 可能 **12～15/19**（paren 类语义对已修可能直接过） |
| `verify_pytest` 失败 | **仍在**（greet/range 是真 generate 问题，P1 攻） |
| `exception` | **仍在**（bench_no_rig_search 基础设施，与终判无关） |

**短期通过率下降也是正常结果**——表示 eval 开始在说真话。

---

## 6. 验收命令

```bash
# 单元 + 契约（无 Ollama）
python -m pytest tests/test_eval_runner.py tests/test_harness_verify_align.py tests/test_eval_contract.py -q

# 单题 live（可选，需 Ollama）
python eval/run_eval.py --task syntaxerror_paren --skip-preflight
```

---

## 7. 后续

- **P1 generate 攻坚**：[`phase8.2.md`](./phase8.2.md)

## 8. 与 Phase 8 关系

| Phase 8 条目 | Phase 8.1 覆盖 |
|--------------|--------------|
| P0-1 `HARNESS_LOCK_TESTS` | ✅ 本阶段 |
| P0-2 inverted skip | ✅ 本阶段 |
| P0-3～P0-6 README 叙事 | ❌ 仍属 Phase 8 P0 |
| P1 easy 攻坚 | ⏳ 8.1 结项后；终判统一是 P1 前置 |

---

## 8. 变更日志

| 日期 | 说明 |
|------|------|
| 2026-06-09 | Phase 8.1 文档创建；P0 终判统一开始执行 |
| 2026-06-09 | 代码落地：统一终判、8 题补 pytest、HARNESS_LOCK_TESTS、inverted skip 修复；46 pytest 通过 |

---

*phase8.1.md · Eval 终判统一 · 2026-06-09*
