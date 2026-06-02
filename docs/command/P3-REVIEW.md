# 任务单：P3-REVIEW

## 元信息

- **TASK_ID**: P3-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P3-MAKE-PLAN ✅ · P3-DOCS ✅

---

## 目标

独立复验 **Phase 3 首项**（`make_plan` + `--plan-first` + README）是否达到 [`struct/phase3.md`](../struct/phase3.md) §3 Done Definition 与 §4 可靠性契约，并给出 **Phase 3 首项可否结项** 结论。

> 本 REVIEW 仅覆盖 P3-MAKE-PLAN / P3-DOCS；Phase 3 整体仍进行中（§6 后续项未派活）。

---

## 约束

- **不修改业务代码**（发现问题写入回报，交主 Agent 裁决）
- 独立运行 `python -m pytest -q` 与 `python -m ruff check .`
- Phase 1/2 spot-check：治理与 Hook 相关测试仍绿
- 对照 prior feedback，不重复实现细节审查

---

## 交付物

- 回报：[`feedback/P3-REVIEW.md`](../feedback/P3-REVIEW.md)
- 结论：**通过** / **不通过**（含 Blocker 列表）

---

## 验收标准

- [ ] `struct/phase3.md` §3 Done Definition 九条逐项有证据（测试名 / README / 代码路径）
- [ ] §4 可靠性契约表格逐项核对
- [ ] README 与实现无矛盾（spot-check `make_plan`、`--plan-first`、`/memory`）
- [ ] pytest / ruff 独立复验输出附在回报
- [ ] 明确 **Phase 3 首项** 可否结项（非整个 Phase 3）

---

## 参考资料

- [`feedback/P3-MAKE-PLAN.md`](../feedback/P3-MAKE-PLAN.md)
- [`feedback/P3-DOCS.md`](../feedback/P3-DOCS.md)
- [`struct/phase3.md`](../struct/phase3.md)
- [`feedback/P2-REVIEW.md`](P2-REVIEW.md)（格式参考）

---

*主 Agent 下达*
