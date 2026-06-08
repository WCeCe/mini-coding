# Eval 报告

| 任务 | 结果 | failure_type | 失败环节 | 原因 | 耗时(ms) |
|------|------|--------------|----------|------|----------|
| syntaxerror_paren | fail | expect_files | expect_files | calc.py 内容与期望不符 | 108303 |
| nameerror_greet | fail | exception | exception | timed out | 161493 |
| off_by_one_sum | fail | fallback_open | verify | pytest 失败（exit 1）：F                                                                        [100%] ================================== FAILURES =================================== _______________________________ test_sum_first ________________________________      def test_sum_first(): >       assert sum_first(3) == 6 E       assert 3 == 6 E        +  where 3 = sum_first(3)  tests\test_sum.py:4: AssertionError =========================== short test summary info =========================== FAILED tests/test_sum.py:: | 109393 |
| missing_return_abs | fail | fallback_open | verify | pytest 失败（exit 1）：F                                                                        [100%] ================================== FAILURES =================================== __________________________________ test_abs ___________________________________      def test_abs(): >       assert abs_val(-3) == 3 E       assert None == 3 E        +  where None = abs_val(-3)  tests\test_abs.py:4: AssertionError =========================== short test summary info =========================== FAILED tests/test_abs.py::te | 109866 |
| no_file_hint_add | fail | fallback_open | verify | pytest 失败（exit 1）：F                                                                        [100%] ================================== FAILURES =================================== __________________________________ test_add ___________________________________      def test_add(): >       assert add(2, 3) == 5 E       assert -1 == 5 E        +  where -1 = add(2, 3)  tests\test_calc.py:4: AssertionError =========================== short test summary info =========================== FAILED tests/test_calc.py::test_add | 107066 |
| bench_retry_off_by_one | fail | fallback_open | verify | pytest 失败（exit 1）：F                                                                        [100%] ================================== FAILURES =================================== _______________________________ test_sum_first ________________________________      def test_sum_first(): >       assert sum_first(3) == 6 E       assert 3 == 6 E        +  where 3 = sum_first(3)  tests\test_sum.py:4: AssertionError =========================== short test summary info =========================== FAILED tests/test_sum.py:: | 107070 |
| import_chain_rate | fail | fallback_open | verify | pytest 失败（exit 1）：F                                                                        [100%] ================================== FAILURES =================================== ________________________________ test_compute _________________________________      def test_compute(): >       assert compute() == 20 E       assert 2000 == 20 E        +  where 2000 = compute()  tests\test_compute.py:4: AssertionError =========================== short test summary info =========================== FAILED tests/test_comp | 103138 |
| logic_median_even | fail | fallback_open | verify | pytest 失败（exit 1）：.F                                                                       [100%] ================================== FAILURES =================================== ______________________________ test_median_even _______________________________      def test_median_even(): >       assert median([1, 2, 3, 4]) == 2.5 E       assert 3 == 2.5 E        +  where 3 = median([1, 2, 3, 4])  tests\test_stats.py:7: AssertionError =========================== short test summary info =========================== FA | 136466 |

## Summary

| 指标 | 值 |
|------|-----|
| passed | 0/8 |
| outcome_ok | 0/8 |
| pipeline_ok（有契约任务） | 0/3 |

## 分步结果（失败任务）

- **syntaxerror_paren**：locate:ok → generate:ok → verify:ok → expect_files:fail
- **nameerror_greet**：locate:ok → generate:fail → exception:fail
- **off_by_one_sum**：locate:ok → generate:fail → verify:fail
- **missing_return_abs**：locate:ok → generate:fail → verify:fail
- **no_file_hint_add**：locate:ok → generate:fail → verify:fail
- **bench_retry_off_by_one**：locate:ok → generate:fail → verify:fail
- **import_chain_rate**：locate:ok → generate:fail → verify:fail
- **logic_median_even**：locate:ok → generate:fail → verify:fail

## 架构痛点聚合（failure_type）

| failure_type | 数量 | 任务 |
|--------------|------|------|
| fallback_open | 6 | `off_by_one_sum`, `missing_return_abs`, `no_file_hint_add`, `bench_retry_off_by_one`, `import_chain_rate`, `logic_median_even` |
| expect_files | 1 | `syntaxerror_paren` |
| exception | 1 | `nameerror_greet` |

## 建议优先改动

1. `mini_coding_agent/modes/graph/runner.py + 上游节点` — 6 条 fallback_open
2. `任务设计 / generate` — 1 条 expect_files
3. `调用栈` — 1 条 exception
