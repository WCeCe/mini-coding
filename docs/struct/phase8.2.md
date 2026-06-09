# Phase 8.2 — Generate 攻坚（P1）

> **状态**：✅ 代码 + live 结项（2026-06-09）  
> **前置**：[`phase8.1.md`](./phase8.1.md) 终判统一 ✅  
> **总纲**：[`phase8.md`](./phase8.md)

---

## 0. P1 要解决什么（相对 8.1）

8.1 修了**阅卷**（pytest 终判、消灭 expect_files）。  
P1 修**出题侧 + 模型侧**：让 8B 在 retry 时**读懂测试在要什么**。（五意图模板仍留在 `templates/`，eval 现阶段只做 fix_bug，后续补齐其余四类。）

**诚实边界**：

| 能在代码里保证 | 不能靠改 prompt 保证 |
|----------------|----------------------|
| generate prompt 含测试 assert 规格 | 8B 一定服从规格 |
| retry 强调 AssertionError 语义 | `bench_no_rig_search` 超时/infra |
| 五意图模板留在 `templates/` 待后续补齐 | live 19 题全过 |

P1 **目标数字**（Phase 8）：easy **6/14 → ≥8/14**，需 **live Ollama** 验证；本阶段代码结项 ≠ 数字已达成。

---

## 1. post74 剩余失败（8.1 后预期变化）

| failure_type | post74 题 | 8.1 后预期 | P1 动作 |
|--------------|-----------|------------|---------|
| expect_files（5） | paren, colon, max, index, double | **终判不再产生**；若语法/逻辑仍错 → verify_pytest | 语法类靠 test spec + syntax hint |
| verify_pytest（2） | greet, off_by_one_range | **仍可能挂** | **test spec block** + retry 强化 |
| exception（1） | bench_no_rig_search | **仍可能挂** | 不在 P1 承诺修复 |

### 1.1 根因（greet，答辩必问）

- 测试：`assert greet("Ada") == "Ada"`（返回参数本身）
- 模型三次：`return f'Hello, {name}'`（自以为「问候函数」）
- retry 只有压缩 AssertionError，**未强调「按 assert 字面行为」**

P1 对策：**从 locate 测试 snippet 提取 assert → 独立「测试规格」块**。

---

## 2. 代码变更（P1 执行清单）

### P1-A — generate：测试规格 + retry（核心）

| 项 | 说明 |
|----|------|
| `_test_spec_block()` | 从 locate snippets 中提取 `tests/` 下 `assert` 行，写入 prompt |
| `_syntax_repair_hint()` | goal 含 SyntaxError 时提示补括号/冒号、保持语义 |
| `_retry_block()` 增强 | AssertionError 时强调满足 assert，勿加问候/格式化 |

**验收（FakeModel，无 Ollama）**：

- `test_generate_test_spec_block`：prompt 含 `assert greet("Ada") == "Ada"`
- 现有 contract + harness 测试仍绿

### P1-B — 五意图（不归档）

曾短暂将非 fix_bug 模板迁 `experimental/`，**已撤回**：五类 DAG 模板均在 `modes/graph/templates/`，`planner.load_template` 统一从该目录加载；`test_harness_five_intents.py` 留在默认 pytest 集。

### P1-C — 文档同步

- 更新 [`phase8.md`](./phase8.md) §3 失败模式表（expect_files 行标注 8.1）
- live baseline（P1-7）：`eval/baselines/live-qwen2.5-coder-7b-post81.json`（**需 Ollama 跑完后写入**）

---

## 3. 结项标准

### 代码结项（不依赖 Ollama）

- [x] P1-A 代码落地（generate test spec）
- [x] `pytest` 默认集全绿：**252 passed**, 1 skipped, 14 deselected
- [x] `test_generate_test_spec.py` 通过
- [x] 五意图模板仍在 `templates/`（无 experimental 归档）
- [x] `test_discovered_bugs` 对齐 8.1 `method: pytest`

### 数字结项（需 live）

- [x] 单题探针（2026-06-09，`qwen2.5-coder:7b`）：
  - `nameerror_greet` ✅（1× generate，`return name`，test spec 生效）
  - `syntaxerror_paren` ✅（1× generate，补 `)`，syntax hint + test spec）
  - `off_by_one_range` ❌（3× generate 仍错 range 逻辑，verify_pytest）
- [x] 全量 19 live：**18/19**（`post82`，2026-06-09）
- [x] easy **12/13**（≥8/14 目标达成；`tasks.json` 当前仅 13 条 easy）
- [x] `--save-baseline` → `eval/baselines/live-qwen2.5-coder-7b-post82.json`
- [x] 归档 → `eval/runs/live/2026-06-09_post82-full-19tasks.json`

**仍挂（唯一）**：`off_by_one_range` — 3× generate 后 `range(n-1,0,-1)` 逻辑仍错；test spec 不足以教 8B 修 off-by-one（需 P2 或更强 hint / 更多 retry 策略）。

---

## 4. 纪律（每攻一题）

1. 只看一条 stage_trace  
2. 只改一个策略（本阶段：统一 test spec，不单题特调）  
3. `--task <id>` live → 再全量 19  

---

## 5. 变更日志

| 日期 | 说明 |
|------|------|
| 2026-06-09 | Phase 8.2 文档；P1 generate 开始执行 |
| 2026-06-09 | 撤回 experimental 归档；五意图模板保留 `templates/` |
| 2026-06-09 | 代码结项：252 pytest 绿；单题 live greet/paren 过、off_by_one 仍挂；全量 post82 跑批 |
| 2026-06-09 | live 结项：post74 11/19 → post82 **18/19**；easy 12/13；仅 off_by_one_range 挂 |

---

*phase8.2.md · P1 generate 攻坚 · 2026-06-09*
