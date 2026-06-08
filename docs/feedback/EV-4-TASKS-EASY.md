# EV-4-TASKS-EASY — 子 Agent 回报

---

## 元信息

- **TASK_ID**: EV-4-TASKS-EASY
- **状态**: 完成
- **依赖**: EV-2-GRADING-SCHEMA ✅

---

## 方案摘要

### 目标

将 easy 档 `fix_bug` 任务从 5 条扩至 **≥12 条**，覆盖 NameError、SyntaxError、ImportError、运算符/比较符、off-by-one、缺 return、空 body 等；保持 `--fake` 全绿。

### 设计决策

1. **沿用单文件 `eval/tasks.json`** — 新 easy 任务插入原 5 条与 medium 3 条之间，不拆目录。
2. **grading 分配** — 4 条 `tests_only` + `lock_tests`（含 pytest 的 ImportError / 缺 return / off-by-one）；4 条 `exact`（比较符、冒号、索引、空 body）。
3. **Fake 队列** — 全部新任务均有 `expect_files`，`build_fake_outputs` 可反推 patch，无需改 `run_eval.py`。

### 新增 7 条 easy 任务

| id | 场景 | grading | verify |
|----|------|---------|--------|
| `importerror_sqrt` | ImportError `math.sqr` | tests_only | pytest |
| `missing_return_abs` | 缺 return | tests_only | pytest |
| `wrong_comparison_max` | 比较符写反 | exact | py_compile |
| `syntaxerror_colon` | 缺冒号 SyntaxError | exact | py_compile |
| `nameerror_index` | NameError `idx` | exact | py_compile |
| `off_by_one_range` | range 下界 off-by-one | tests_only | pytest |
| `empty_body_double` | 函数体 `pass` | exact | py_compile |

easy 合计 **12 条**（原 5 + 新 7）；全任务集 **15 条**（含 medium 3 条）。

### 改动文件

| 路径 | 说明 |
|------|------|
| `eval/tasks.json` | +7 easy 任务 |
| `eval/README.md` | easy 任务表 12 条、合计 15 条 |
| `tests/test_eval_runner.py` | easy ≥12 断言、新任务 fake pass 参数化、bug 类型覆盖测 |
| `docs/feedback/EV-4-TASKS-EASY.md` | 本回报 |

---

## 验收自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| easy ≥12 条 | ✅ | 12 条，`tier: easy` |
| 唯一 id、不重复原 5 条 | ✅ | 7 个新 id |
| bug 类型覆盖 | ✅ | `test_easy_tasks_bug_type_coverage` |
| `--fake` 全绿 | ✅ | 见下方 |
| pytest + ruff | ✅ | 见下方 |

---

## 验证结果

### `python eval/run_eval.py --fake`

```
**合计**：15/15 通过
```

（12 easy + 3 medium 全绿）

### `python -m pytest tests/test_eval_runner.py -q`

```
30 passed in 293.55s
```

### `python -m ruff check .`

```
All checks passed!
```

### 备注

`missing_return_abs` 初版 setup 无尾行，`_extract_patch_snippet` 产出空 `old_text` 导致 fake 失败；改为末尾 `pass` → `return x` 单行替换后通过。

---

## 主 Agent 复审

- **结论**: **通过**
- **备注**: 2026-06-05 easy 12 条；fake 15/15。
