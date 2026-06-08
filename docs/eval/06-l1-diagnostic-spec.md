# L1 组件诊断规格

> 返回索引：[`README.md`](./README.md) · 验证清单：[`05-pipeline-checklist.md`](./05-pipeline-checklist.md)

L1 在**零 LLM** 条件下，对每个架构模块做输入→输出契约测试。本文列出全部规划用例 ID、样本、期望与量化门槛，供 `tests/diagnostic/` 实现时逐条对照。

---

## 0. 实现状态（2026-06-08 · Batch 5）

| 模块 | 规格章节 | 实现位置 | 状态 |
|------|----------|----------|------|
| slots + locate | §3–§4 | `tests/diagnostic/test_slots_locate.py` | ✅ SL/L 子集 + D1–D3 |
| Gate parse/route | §2 | `tests/test_harness_gate.py` | ✅ 分散（非 diagnostic/） |
| protocol | §5 | `tests/test_generate_robust.py` | ✅ 分散 |
| verify_rules | §6 | `tests/test_harness_verify_align.py` | ✅ 分散 |
| error_format | §7 | `tests/test_harness_error_format.py` | ✅ 分散 |

**CI 入口**：`pytest tests/diagnostic/ -q`（仅跑已实现 diagnostic 文件；Gate/protocol 等由 harness 套件覆盖）。

规划中的 `test_gate_parse.py` 等**未创建**；Batch 8 可选从 harness 测试抽取到 `diagnostic/`。

---

## 1. 文件与模块映射

| 文件 | 被测模块 | 导入路径 | 状态 |
|------|----------|----------|------|
| `test_slots_locate.py` | slots + locate | `modes.graph.slots`, `nodes.locate` | ✅ 在 repo |
| `test_gate_parse.py` | Gate 解析与路由 | `modes.graph.gate` | 📋 → `test_harness_gate.py` |
| `test_protocol_generate.py` | protocol 解析 | `platform.protocol` | 📋 → `test_generate_robust.py` |
| `test_verify_rules.py` | verify 规则 | `modes.graph.verify_rules` | 📋 → `test_harness_verify_align.py` |
| `test_error_format.py` | retry 错误摘要 | `modes.graph.error_format` | 📋 → `test_harness_error_format.py` |

---

## 2. Gate（G 系列）

### 2.1 test_gate_parse.py

| ID | 输入 | 期望 | 备注 |
|----|------|------|------|
| G-01 | Model 输出 `{"intent_id":"fix_bug","confidence":"high"}` | `route=harness_pipeline`, `intent_id=fix_bug` | 正常 fix_bug |
| G-02 | `{"intent_id":"fix_bug","confidence":"low"}` | `route=open` | 低置信降级 |
| G-03 | 非 JSON 文本 `fix the bug` | `confidence=low`, `route=open`, `intent_id=""` | 安全降级 |
| G-04 | `{"intent_id":"add_test","confidence":"high"}` | `route=open`, 保留 unknown intent | 未知意图 |
| G-05 | Markdown 围栏 JSON | 解析成功 | `extract_json_object` |
| G-06 | `{"intent_id":"explain","confidence":"high"}` | `route=harness_pipeline` | explain 仍进 pipeline（非 B3） |
| G-07 | 空字符串 | `route=open` | 边界 |

**量化门槛**：G-01–G-07 全部 100% pass。

---

## 3. Slots（SL 系列）

### 3.1 test_slots_locate.py — slots 部分

测试函数：`extract_files_hint`, `extract_symbols_hint`, `fill_slots`, `detect_test_command`。

#### 3.1.1 文件提取（D1：≥90%，≥18/20）

| ID | user_message 摘要 | workspace | 期望 files_hint |
|----|-------------------|-----------|-----------------|
| SL-01 | `File "calc.py", line 2` traceback | 有 calc.py | `["calc.py"]` |
| SL-02 | `请修复 calc.py 中的错误` | 有 calc.py | `["calc.py"]` |
| SL-03 | `File "src/utils/helper.py", line 10` | — | `["src/utils/helper.py"]` |
| SL-04 | `修复 greet.py 和 farewell.py` | — | 含两者，顺序保序 |
| SL-05 | Windows 路径 `File "foo\\bar.py"` | — | 规范为 `foo/bar.py` |
| SL-06 | 绝对路径在 workspace 内 | root=/proj | 相对化 `calc.py` |
| SL-07 | 绝对路径在 workspace 外 | — | 保留原路径或跳过 |
| SL-08 | 无路径纯描述 | — | `[]` |
| SL-09 | `.json` / `.md` 路径 | — | 匹配 `_MESSAGE_PATH` |
| SL-10 | 重复路径只出现一次 | — | 去重 |

#### 3.1.2 符号提取（D2：≥85%）

| ID | user_message 摘要 | 期望 symbols_hint |
|----|-------------------|-------------------|
| SL-11 | `NameError: name 'foo' is not defined` | 含 `foo` |
| SL-12 | `AttributeError: 'NoneType' object has no attribute 'bar'` | 含 `bar` |
| SL-13 | `ImportError: cannot import name 'baz'` | 含 `baz` |
| SL-14 | `ModuleNotFoundError: No module named 'qux'` | 含 `qux` |
| SL-15 | `add(2, 3) 得到 -1`（无 traceback） | 含 `add` |
| SL-16 | 纯 explain：`解释 calc.py 做什么` | 不含误导 symbol 或为空 |
| SL-17 | `in add` traceback 行 | 含 `add` |

#### 3.1.3 test_command

| ID | workspace 条件 | 期望 |
|----|----------------|------|
| SL-18 | 存在 `tests/` 目录 | `python -m pytest -q` |
| SL-19 | 存在 `pytest.ini` | 同上 |
| SL-20 | `pyproject.toml` 含 pytest | 同上 |
| SL-21 | 无 pytest 迹象 | `None` |

#### 3.1.4 fill_slots 集成

| ID | intent_id | 期望 slots 键 |
|----|-----------|---------------|
| SL-22 | fix_bug | goal, files_hint, symbols_hint, test_command? |
| SL-23 | project_ops | 额外 ops_allowlist |
| SL-24 | fix_bug + skill_name | skill_name 透传 |

---

## 4. Locate（L 系列）

### 4.1 test_slots_locate.py — locate 部分

在临时目录搭建 workspace，调用 `run_locate(ctx)` 或等价入口。

| ID | 前置条件 | 期望 | 门槛 |
|----|----------|------|------|
| L-01 | files_hint=[calc.py], 文件存在 | snippets 含 `# calc.py:` 行号 | D3: 100% |
| L-02 | 有 RIG index.db | `used_rig=True`, snippets 非空 | 100% |
| L-03 | 无 index.db, 有 symbols_hint | search 回退, snippets 非空 | 100% |
| L-04 | files_hint 指向不存在文件 | 不 crash；snippet 可能空 | 不 crash |
| L-05 | 空 workspace | ok=True（当前行为）或 P2-b 后 fail | 文档化 |
| L-06 | 多文件 hint | 多个 snippet | — |
| L-07 | snippet 行内容为真实源码非占位 | 含 `def ` 或错误行 | D3 |

**D3 定义**：当 `files_hint` 非空且文件存在时，至少 1 个 snippet 匹配正则 `# .+\.py:\d+` 且含源码行。

---

## 5. Protocol（GN 系列）

### 5.1 test_protocol_generate.py

| ID | model raw 输入 | parse() 结果 | generate 行为 |
|----|----------------|--------------|---------------|
| GN-01 | 合法 JSON tool patch_file | kind=tool | 可执行 |
| GN-02 | 尾 `}` 多余 | kind=tool（容错） | 可执行 |
| GN-03 | f-string 引号 `new_text` | kind=tool | 可执行 |
| GN-04 | XML `<tool name="write_file">` | kind=tool | 可执行 |
| GN-05 | `<final>done</final>` | kind=final | generate **fail** |
| GN-06 | 纯文本无标签 | kind=retry 或 text | generate **fail** |
| GN-07 | tool name 非法 | — | generate fail |
| GN-08 | 畸形 JSON 缺闭合 | — | 非 tool |

与 `tests/test_generate_robust.py` 分工：robust 测 **generate 节点 E2E**；diagnostic 测 **parse() 纯函数**。

---

## 6. Verify Rules（V 系列）

### 6.1 test_verify_rules.py

| ID | 场景 | 期望 |
|----|------|------|
| V-01 | workspace 有 tests/, 改动 .py 逻辑仍错 | `run_task_verify` pytest fail |
| V-02 | setup tests/ 被 agent 修改 | `check_lock_tests_from_setup` 报错 |
| V-03 | 无 tests/, 语法错误 | py_compile fail |
| V-04 | 无 tests/, 语法正确 | py_compile pass |
| V-05 | generate.path under tests/ | harness verify 第一步 reject |
| V-06 | test_baseline 快照一致 | lock pass |

---

## 7. Error Format（R 系列）

### 7.1 test_error_format.py

| ID | 输入 verify.message | 期望 |
|----|---------------------|------|
| R-01 | 长 pytest 输出 (>2000 字符) | 压缩 ≤800 字符 |
| R-02 | 多行 traceback | ≤8 行 |
| R-03 | 空 message | 非空 fallback 字符串 |
| R-04 | 含 `assert` 行 | 保留 assert 上下文 |

---

## 8. 量化门槛汇总

| 指标 ID | 计算方式 | 门槛 | CI 失败动作 |
|---------|----------|------|-------------|
| D1 | SL-01–SL-10 pass rate | ≥ 90% | pytest fail |
| D2 | SL-11–SL-17 pass rate | ≥ 85% | pytest fail |
| D3 | L-01,L-03,L-07 在有 hint 时 | 100% | pytest fail |
| G-all | G-01–G-07 | 100% | pytest fail |

实现建议：用 `@pytest.mark.parametrize` + 汇总 fixture 在 session 末打印准确率。

---

## 10. 与现有测试的去重

| 已有文件 | L1 不重复测 |
|----------|-------------|
| `test_harness_fix_bug_e2e.py` | 完整 pipeline 成功路径 |
| `test_harness_gate.py` | gate_log CLI 集成 + **G 系列 parse** |
| `test_generate_robust.py` | **GN 系列 protocol** + generate E2E |

L1 **补充**纯函数级样本集与 **D1–D3 量化门槛**（`test_slots_locate.py`），不替代 harness E2E。

---

*06-l1-diagnostic-spec.md · Batch 5 对齐实际布局 · 2026-06-08*
