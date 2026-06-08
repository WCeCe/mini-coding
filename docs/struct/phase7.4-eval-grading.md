# Phase 7.4 — 写盘换行 + nameerror_greet 任务改版

> **状态**：✅  
> **总纲**：[`phase7.md`](./phase7.md)

---

## 1. 目标

| 项 | 问题 | 方案 |
|----|------|------|
| **7.4-A** | `syntaxerror_paren` exact 失败：补丁对但缺末尾 `\n` | `atomic_write_text` 自动 `ensure_trailing_newline` |
| **7.4-B** | `nameerror_greet`：模型写 f-string greeting，gold 要 `return name` | 任务改为 **`tests_only` + pytest**，用行为约束语义 |

---

## 2. 7.4-A — 尾随换行（产品级）

**文件**：`platform/util.py`

- `ensure_trailing_newline(content)`：非空且不以 `\n` 结尾则补一个
- `atomic_write_text` 写盘前统一调用

**影响**：所有经 governance 的 `write_file` / `patch_file`；eval exact 与真实仓库一致。

**测试**：`tests/test_mini_coding_agent.py::test_patch_file_appends_trailing_newline_when_missing`

---

## 3. 7.4-B — `nameerror_greet` 任务改版

**文件**：`eval/tasks.json`

| 字段 | 改前 | 改后 |
|------|------|------|
| `grading` | `exact` | `tests_only` |
| `lock_tests` | — | `true` |
| `verify` | `py_compile` | `pytest` |
| `setup_files` | 仅 `greet.py` | + `tests/test_greet.py` |
| `message` | traceback | pytest 失败句式 |

**测试断言**：

```python
assert greet("Ada") == "Ada"
assert greet("Bob") == "Bob"
```

- `return name` → ✅  
- `return f'Hello, {name}!'` → ❌（verify pytest 失败，符合真实场景）

`expect_files` 保留作参考，**终判以 pytest 为准**。

---

## 4. Live 验收（2026-06-08）

| 任务 | 结果 | 说明 |
|------|------|------|
| `syntaxerror_paren` | **PASS** | 写盘补 `\n` 后 exact 通过 |
| `nameerror_greet` | **FAIL** `verify_pytest` | 任务改版生效：pytest 正确拒绝 f-string；模型 3 次 retry 仍写 `Hello, Ada!` |

报告：`eval/runs/experiments/2026-06-08_phase74-*.json`

**后续**（非 7.4 范围）：retry prompt 应强调测试断言 `== name`；或加强 generate NameError 提示。

---

*phase7.4-eval-grading.md · 2026-06-08*
