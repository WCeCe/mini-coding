# Eval 修复与加固计划（波次 C）

> **状态**：✅ **结项**（EV-1–7 + EV-REVIEW · 2026-06-05）  
> **前置**：Phase 5 + 黄金闭环 GL-1–5 ✅  
> **派活索引**：[`command/EVAL-REPAIR-OVERVIEW.md`](../command/EVAL-REPAIR-OVERVIEW.md)  
> **触发原因**：主 Agent 对现有 eval 做严格审计 + 本机 `--live` 复验 **2/5**（与 GL-5 基线一致）

---

## 1. 问题陈述（诚实诊断）

现有 `eval/` 在 GL 阶段完成了「黄金闭环能跑通」的 MVP，但**不能**作为「agent 有多强」的可靠论据。

| 发现 | 严重度 | 证据 |
|------|--------|------|
| `--fake` 5/5 从 `expect_files` **反推**标准答案，测的是管线接线而非智能 | P0 | `build_fake_outputs()` |
| harness `verify` 与 eval 终判 **双标准**（py_compile 过 ≠ 逻辑对） | P0 | GL-5 `off_by_one_sum`：harness verify ok、`expect_files` fail |
| 5 条任务均属 **简单档**（单文件、消息含路径、一行修复） | P1 | `tasks.json` |
| Locate / Gate 几乎未被考到（`slots` 正则提取 `files_hint`） | P1 | `slots.py` |
| `expect_files` 精确匹配 **误杀**合法变体、**漏检**测试文件被改 | P1 | 评分设计 |
| live **2/5**（`qwen2.5-coder:7b`）：Generate 协议/patch 为主瓶颈 | P1 | GL-5 + 2026-06-05 复验 |
| CI 绿仅保证 fake 管线，不保证 live 能力 | P2 | `test_run_eval_cli_fake_subprocess` |

**综合可靠性（主 Agent 评分）**：作为 agent 能力证明 **3/10**；作为 harness 回归 **6/10**。

**产品决策（已对齐）**：

1. **不替换**现有 `eval/` 框架，在之上加固。  
2. **不引入**新 pip 依赖（延续 GL 约束）。  
3. **接受** live 在加固后短期仍可能 &lt;5/5——诚实指标优先于刷分。  
4. **分拆**「管线回归」与「agent 能力」两种指标，避免 fake 5/5 自嗨。

---

## 2. 目标与非目标

### 2.1 目标

| # | 目标 | 可验证标志 |
|---|------|------------|
| G1 | harness `verify` 与 eval 终判 **语义一致**，消除「verify ok 但答案错」假阳性 | 回归测 + `off_by_one_sum` 类任务行为修正 |
| G2 | 任务评分支持 **`grading` 模式**，默认以测试/编译为准，精确匹配可选 | `tasks.json` schema + `run_eval.py` |
| G3 | live 主瓶颈（Generate 协议、patch 匹配）有 **针对性修复** | live 基线可对比（允许仍 2–4/5） |
| G4 | 任务集按 **简单 / 一般 / 困难** 分档扩展 | ≥12 简单 + ≥3 一般 + 困难档占位 |
| G5 | eval 产出 **结构化分步结果** + **基线对比** | `--save-baseline` / `--compare` |
| G6 | 文档与 CI **明确区分** harness-eval vs agent-eval | README、struct、可选 CI step |

### 2.2 非目标（本波次不做）

- SWE-bench / Harbor 接入  
- 新增 pip 包（DeepEval、agentevals 等）  
- 非 `fix_bug` 意图的 live eval 大盘  
- Gate 规则化混合（留给 5.8）  
- 默认 `--harness on`

---

## 3. 任务难度分档（契约）

后续 `tasks.json`（或目录式任务）须标注 `tier`：

| tier | 定义 | 示例 | 本波次数量目标 |
|------|------|------|----------------|
| `easy` | 单文件；消息含路径或 traceback；≤1 行逻辑修复 | 现有 5 条 | **12–15** |
| `medium` | 多文件 **或** 消息不点名文件；需读测试/符号；Gate 无歧义 | import 链 bug、无 traceback 的描述 | **3–5** |
| `hard` | 5+ 文件小项目；跨模块；需多步推理或 verify retry | 占位 + 1 条可选 | **0–1**（占位文档即可） |

**评分原则**：

| `grading` | 含义 | 适用 |
|-----------|------|------|
| `tests_only` | 以任务级 `verify`（pytest/py_compile）为准；**不**要求 `expect_files` | medium+ 默认 |
| `exact` | `expect_files` 字节级匹配（现有行为） | easy 可选保留 |
| `lock_tests` | 除 `setup_files` 中测试路径外，测试文件内容不得变 | 凡含 `tests/` 的任务 |

---

## 4. 波次 C 子任务（EV-1–7）

严格顺序：**EV-1 → EV-2** 可并行筹备，但 **EV-2 依赖 EV-1 的 verify 行为约定**；**EV-3** 可与 EV-2 并行；**EV-4/5** 依赖 EV-2 schema；**EV-6** 依赖 EV-1–3；**EV-7** 最后；**EV-REVIEW** 收口。

| 顺序 | ID | 名称 | 优先级 | 改码范围 |
|------|-----|------|--------|----------|
| 1 | **EV-1** | Verify 对齐 | P0 | `nodes/verify.py`、eval 断言逻辑 |
| 2 | **EV-2** | 评分 schema（`grading`/`tier`） | P0 | `tasks.json`、`run_eval.py`、README |
| 3 | **EV-3** | Generate 鲁棒性 | P0 | `protocol.py`、`nodes/generate.py`（小步） |
| 4 | **EV-4** | 任务集·简单档扩展 | P1 | `eval/tasks.json` 或 `eval/tasks/` |
| 5 | **EV-5** | 任务集·一般档 | P1 | 新任务 + 单测 |
| 6 | **EV-6** | 结构化报告 + 基线对比 | P1 | `run_eval.py` |
| 7 | **EV-7** | 文档 + CI 分层 | P2 | README、struct、`.github/workflows` |
| 8 | **EV-REVIEW** | 总验收 | — | 否 |

任务单：[`command/EVAL-REPAIR-OVERVIEW.md`](../command/EVAL-REPAIR-OVERVIEW.md)。

---

## 5. 技术要点（EV-1 / EV-2 摘要）

### 5.1 EV-1：Verify 对齐

**问题**：`off_by_one_sum` 在 harness 内 `verify ok`，但磁盘内容与 `expect_files` 不符；4/5 条 easy 任务 harness verify 仅 `py_compile`，不验语义。

**要求**：

1. 工作区存在 `tests/`（或 `slots.test_command`）时，harness `verify` **必须**执行该测试命令，不得以「仅改动的 `.py` py_compile 通过」提前成功。  
2. eval 终判与 harness 使用 **同一套** verify 规则（任务级 `verify` 不重复造轮子）。  
3. 增加 pytest：**错误修复仍 py_compile 过、pytest 应 fail** 的用例。  
4. 含 `tests/` 的任务：检测测试文件哈希/内容，**被 agent 修改则 fail**（`lock_tests` 行为，可与 EV-2 合并实现）。

### 5.2 EV-2：评分 schema

扩展 `tasks.json` 字段（向后兼容）：

```json
{
  "id": "off_by_one_sum",
  "tier": "easy",
  "grading": "tests_only",
  "lock_tests": true,
  "expect_files": { "...": "..." },
  "verify": "pytest"
}
```

- 缺省 `grading`：有 `expect_files` → `exact`；仅 `verify` → `tests_only`。  
- `tests_only` 时 `expect_files` 可为空或仅作文档参考。  
- FakeModel 队列生成逻辑须随 `grading` 调整（`exact` 仍用现有反推）。

### 5.3 EV-3：Generate 鲁棒性

针对 live 失败模式（GL-5 + 2026-06-05）：

| 失败 | 方向 |
|------|------|
| `old_text` 0 次匹配 | patch 前规范化（尾随换行、缩进提示）或 strip 容错（**限 fix_bug**） |
| `generate 须返回 tool`（含合法-looking `<tool>`） | `protocol.parse` 对嵌套引号 / 尾 `}` 的容错 |
| 超时 | eval `--live` 文档化逐 task；可选增大默认 timeout（不改为 CI 要求） |

**约束**：不削弱 governance 安全边界；容错须有 pytest 回归。

---

## 6. 里程碑与基线

| 标记 | 任务 | 标志 |
|------|------|------|
| M0 | EV-1 + EV-2 | fake 全绿；`off_by_one_sum` 类任务无 harness/eval 双标准 |
| M1 | EV-3 | live 复跑有记录；至少 1 条原 fail → pass 或失败原因变化可解释 |
| M2 | EV-4 + EV-5 | easy ≥12、medium ≥3；medium 在 live 下允许 0/N |
| M3 | EV-6 | `eval/baselines/` + `--compare` 可用 |
| M4 | EV-7 + EV-REVIEW | 文档诚实表述；CI 区分两类 eval |

**Live 基线（冻结对比点）**：

| 环境 | 模型 | 结果 | 日期 |
|------|------|------|------|
| Windows | `qwen2.5-coder:7b` | **2/5** | GL-5 / 2026-06-05 复验 |

EV 波次结束后须更新此表，**禁止**仅报告 fake 通过率。

---

## 7. Done Definition（EV-REVIEW）

- [ ] EV-1：`verify` 与 eval 终判一致；`lock_tests` 或等价机制生效  
- [ ] EV-2：`grading` / `tier` 字段文档化；旧 5 条任务迁移  
- [ ] EV-3：Generate/protocol 有针对 live 失败的 pytest  
- [ ] EV-4：easy 档 ≥12 条；`--fake` 全绿  
- [ ] EV-5：medium 档 ≥3 条；live 结果诚实归档（可 0/N）  
- [ ] EV-6：结构化分步 + 基线对比 CLI  
- [ ] EV-7：README / struct / eval README 区分 harness-eval vs agent-eval  
- [ ] 全量 pytest + ruff 不低于派活前基线  
- [ ] 无新增 pip 依赖  

---

## 8. 风险登记

| 风险 | 缓解 |
|------|------|
| EV-1 改动破坏现有 harness E2E | 先补 pytest 再改 verify；fake 全量回归 |
| `tests_only` 后 easy 任务区分度更低 | easy 保留部分 `exact`；medium 拉区分度 |
| Generate 容错引入错误 patch 被接受 | 容错仅放宽解析，不跳过 governance |
| live 全挂打击士气 | 文档明确：medium 0/N 为预期；看分步报告改方向 |
| 任务集扩大导致 fake 队列难维护 | 目录式任务 + `grading: tests_only` 减少 exact 依赖 |

---

## 9. 与 Phase 5.8+ 关系

| 本波次 | 原 5.8+ 路线图 |
|--------|----------------|
| EV-1–3 | 5.13 eval 扩展 + Generate 鲁棒性的 **可执行子集** |
| EV-4–5 | 5.13 任务集扩展的 **分档实现** |
| EV-6 | 新增（原路线图未写清） |
| Gate 混合、RIG 增量 | 仍为 5.8+，**不在**本波次 |

---

*struct/eval-repair-plan · 主 Agent · 2026-06-05*
