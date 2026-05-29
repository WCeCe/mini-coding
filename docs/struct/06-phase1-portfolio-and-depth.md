# Phase 1 作品集定位：深度、亮点与边界

> **读者**：项目所有者（研究生 · 目标岗：AI 大模型应用开发工程师）、主 Agent、子 Agent。
>
> **目的**：在「做得完」和「显得有深度」之间取平衡，让 Phase 1 变更治理成为简历与面试中的**可讲透**亮点。

---

## 1. 目标岗位能力对照（大厂 AI 应用开发 · 常见要求）

| 招聘要求（抽象） | 本项目 Phase 1 如何体现 | 面试一句话 |
|------------------|---------------------------|------------|
| 熟悉 LLM 应用、Tool Calling | 治理插在执行层，不改模型 tool 协议 | 「协议稳定，执行可治理」 |
| Prompt / 上下文管理 | 副作用可审计，不全量 diff 灌进 prompt | 「history 记摘要即可追溯」 |
| Agent 稳定性与异常处理 | 可靠性契约 + 格式 retry 与写盘回滚分工 | 「两类失败分开处理」 |
| 人机协同 / 安全 | diff 审批替代静默写盘 | 「人先看 diff 再批准」 |
| 工程化与测试 | pytest 覆盖副作用，不依赖真 LLM | 「FakeModelClient 锁行为」 |
| 系统设计 / 权衡 | 文档写清做与不做及原因 | 「run_shell 不回滚因不可追踪」 |
| 业务落地意识 | Git 脏树警告 | 「真实仓库常不干净」 |

**留给后续阶段（简历 Roadmap）**：RAG、多模型、Benchmark、Docker 沙箱、分布式。

---

## 2. 五个可写进简历的亮点（方向，非实现细节）

1. **Diff-first 变更治理** — 审批前可见 unified diff  
2. **单次 Tool 级 Checkpoint + 回滚** — 失败可恢复，含外部篡改防护  
3. **可审计 Session** — 事后能回答「改了什么」  
4. **Git-aware 风险提示** — 只读、不替用户 commit  
5. **可测试的 Agent 副作用** — 契约场景有自动化测试  

具体方案由子 Agent 设计，须满足 [`05-phase1-implementation-design.md`](./05-phase1-implementation-design.md) 契约。

---

## 3. 深度上限（工期控制）

| 不做 | 原因 |
|------|------|
| 拆多包 / 微服务 | MVP 优先 |
| Web UI | 终端 diff 足够 demo |
| `run_shell` 回滚 | Phase 2 |
| 一次 ask 全部撤销 | 复杂度过高 |
| 模糊 patch / 自动 commit | 风险大 |
| 新 pip 依赖 | 保持轻量 |

**工期参考**：单人约 **5–8 个工作日**（实现 + 测试 + 文档）。

---

## 4. Phase 1「完成」定义（Done Definition）

主 Agent 与子 Agent 均以本节为**唯一验收标准**。

### 4.1 功能指标

- [ ] `write_file` / `patch_file` 审批时展示 **unified diff**（非原始 tool 参数）
- [ ] 用户拒绝 → **磁盘与改前一致**
- [ ] 批准后写盘失败 → **自动回滚**
- [ ] 新建文件失败回滚 → **文件不存在**
- [ ] 脏 git 工作区 → 审批时有 **警告**
- [ ] `run_shell` 与 Phase 1 前 **行为一致**

### 4.2 工程指标

- [ ] `python -m pytest -q` 全绿（含回归）
- [ ] `python -m ruff check .` 通过
- [ ] 主逻辑仍在 `mini_coding_agent.py` 单文件
- [ ] README 有 **Change Governance** 说明及已知限制

### 4.3 文档指标

- [ ] 实现与 [`05`](./05-phase1-implementation-design.md) 可靠性契约一致
- [ ] 子 Agent `feedback/` 含方案摘要与自证如何满足 Done Definition

---

## 5. Phase 1 任务（主 Agent 只派目标）

| 任务 | 文件 | 性质 |
|------|------|------|
| 变更治理实现 | [`command/P1-CHANGE-GOVERNANCE.md`](../command/P1-CHANGE-GOVERNANCE.md) | 交付 §4 功能+工程指标 |
| 用户文档 | [`command/P1-DOCS.md`](../command/P1-DOCS.md) | 交付 §4.2 README |
| 总验收 | [`command/P1-REVIEW.md`](../command/P1-REVIEW.md) | 对照 §4 勾选 |

子 Agent **自行拆分**实现步骤；须在 `feedback` 中汇报方案，无需与主 Agent 逐步对齐。

---

## 6. 面试叙述模板

> 我在 Mini-Coding-Agent 里加了**变更治理**：模型仍用原有 tool，但写文件前先看 diff，批准后才 checkpoint 和写盘，失败可回滚，session 可审计。  
> 我写了**可靠性契约**并用 pytest 覆盖，不依赖真 LLM。run_shell 回滚和一键撤销故意没做，留给沙箱阶段。

---

*struct/06 · 主 Agent 维护*
