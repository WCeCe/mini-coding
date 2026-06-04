# GL-5-LIVE-EVAL — 子 Agent 回报

---

## 元信息

- **TASK_ID**: GL-5-LIVE-EVAL
- **状态**: 完成

---

## 方案摘要（IMPLEMENT 必填）

1. **`eval/tasks.json`**：由 1 条扩至 **5** 条最小 `fix_bug` 场景（NameError×2、SyntaxError、off-by-one+pytest、运算符错误）。
2. **`eval/run_eval.py`**：
   - `--live` 使用 `OllamaModelClient`；启动前 `check_ollama_available` 预检（exit 2）。
   - `--max-new-tokens`、`--skip-preflight`；失败任务在 Markdown 报告附 **Harness stderr 摘要**。
   - `build_fake_outputs` 增加 **按行 diff 回退**（修复字符级 diff 退化导致 `old_text=""` 的 2 条 Fake 失败）。
3. **`eval/README.md`**：环境、命令、5 条任务表、stderr 定位表、live 工作流。
4. **真实 `--live`**：本机 `qwen2.5-coder:7b`，按 task 逐条跑（避免长批次超时中断）。

未改 Hook / Skill / Gate / 非 fix_bug 模板 / harness 业务节点。

---

## 契约与 Done Definition 自证

| 条目 | 是否满足 | 证据 |
|------|----------|------|
| tasks.json 3–5 条 | ✅ | 5 条，见 README 表 |
| `--live` + OllamaModelClient | ✅ | `run_eval.py` `_build_live_client` + 预检 |
| README 可复现 | ✅ | `eval/README.md` |
| 真实跑 ≥1/N pass | ✅ | **2/5**（见下表） |
| 失败可定位步骤 | ✅ | 报告 `failure_step` + stderr 摘要 |
| `--fake` 全 pass | ✅ | `5/5`；`test_run_eval_cli_fake_subprocess` |
| pytest + ruff | ✅ | 167 passed, 1 skipped；ruff 全绿 |

---

## 首次真实 Ollama 基线（诚实记录）

**环境**：Windows，Ollama `http://127.0.0.1:11434`，模型 `qwen2.5-coder:7b`，`--ollama-timeout 180`，`--max-new-tokens 512`（默认）。

**命令**（逐 task，避免单次全量超时）：

```bash
python eval/run_eval.py --live --model qwen2.5-coder:7b --ollama-timeout 180 --task <task_id>
```

| task_id | 结果 | 失败环节 | 根因简述（对应 Gate/Locate/Generate/Verify） |
|---------|------|----------|-----------------------------------------------|
| nameerror_calc | **pass** | — | Gate → Locate → Generate(patch) → Verify 全 ok；~43s |
| syntaxerror_paren | fail | expect_files* | **Generate**：`patch_file` old_text 未匹配（期望 1 次实际 0）；流水线降级 open；文件未改 |
| nameerror_greet | fail | expect_files* | **Generate**：模型返回 `<tool>…patch_file…</tool>` 但解析/校验未通过（`generate 须返回 tool 调用`）；降级 open |
| off_by_one_sum | fail | expect_files | **Generate**：harness 三步 stderr 均 ok（含 verify），但磁盘内容与 `expect_files` 不完全一致（逻辑修偏或未改到 `range(1, n+1)`） |
| wrong_operator_calc | **pass** | — | 全链路 ok；~76s |

\* 报告层为 `expect_files`（post_check 先失败）；stderr 指向 **generate** 或 **pipeline（降级 open）**。

**合计**：**2/5 通过**（40%）。

### 典型 stderr 片段

**syntaxerror_paren（generate）**：

```
[harness] fix_bug 1/3 locate ok
[harness] fix_bug 2/3 generate fail
[harness] 流水线失败：…patch_file 参数无效…old_text 恰好出现 1 次，实际出现 0 次…
```

**nameerror_greet（generate / 格式）**：

```
[harness] fix_bug 2/3 generate fail
…generate 须返回 tool 调用，收到：<tool>{"name":"patch_file",…"new_text":"return f'Hello, {name}!'"}}…
```

**off_by_one_sum（改错内容，harness verify 仍 ok）**：

```
[harness] fix_bug 1/3 locate ok
[harness] fix_bug 2/3 generate ok
[harness] fix_bug 3/3 verify ok
# 但 expect_files：sum_first.py 内容与期望不符
```

### 结论与后续（不阻塞 GL-5）

- 带 **traceback + 明确变量名** 的 NameError、**单行运算符** 类任务，小模型可闭环。
- **SyntaxError / 括号修补**、**f-string 风格 patch**、**精确 expect 的 off-by-one** 仍易在 Generate 或改码内容上失败。
- 建议下一轮：优先 GL-3 摘要 + Generate prompt/协议（非本任务范围），或放宽 eval `expect_files` 为子串匹配（需主 Agent 批准）。

---

## 交付物

| 路径 | 说明 |
|------|------|
| `eval/tasks.json` | 5 条 fix_bug 任务 |
| `eval/run_eval.py` | live 预检、stderr 摘要、按行 fake patch |
| `eval/README.md` | 用法与定位表 |
| `tests/test_eval_runner.py` | 5 任务、预检、CLI 5/5 |
| `docs/feedback/GL-5-LIVE-EVAL.md` | 本回报 |

---

## 验证结果

```
$ python eval/run_eval.py --fake
**合计**：5/5 通过
```

```
$ python -m pytest tests/test_eval_runner.py -q
9 passed
```

```
$ python -m pytest -q
167 passed, 1 skipped
```

```
$ python -m ruff check .
All checks passed!
```

---

## 风险与未解决问题

- **全量 `--live` 无 `--task`** 约 8–15 分钟，易超时；README 已建议逐条或调大 `--ollama-timeout`。
- **off_by_one_sum**：harness `verify` 节点默认 `py_compile`，任务级 `pytest` 在 `expect_files` 之后才跑；live 失败先体现在精确文件匹配，而非 pytest 摘要。

---

## 主 Agent 复审（由主 Agent 填写）

- **结论**: **通过**
- **备注**: 2026-06-04 主 Agent 复验：`--fake` 5/5；pytest 167 passed；live **2/5**（nameerror_calc、wrong_operator_calc）满足 ≥1/N；失败逐步定位清晰。GL-5 结项 → GL-REVIEW 黄金闭环结项。
