# 任务单：P4-REVIEW

## 元信息

- **TASK_ID**: P4-REVIEW
- **TASK_TYPE**: REVIEW
- **优先级**: P1
- **可以写代码**: 否
- **依赖**: P4-SKILLS ✅ · P4-DOCS ✅

---

## 目标

独立复验 **Phase 4 首项 + 文档**（P4-SKILLS + P4-DOCS）是否达到 [`struct/phase4.md`](../struct/phase4.md) §3.2 Done Definition 与 §3.3 可靠性契约，并给出 **Phase 4 当前交付可否结项** 结论。

> 本 REVIEW 覆盖 P4-SKILLS / P4-DOCS；Phase 4 暂缓项（高级 frontmatter、slash、benchmark）不在范围。

---

## 约束

- **不修改业务代码**（Blocker 写入回报，交主 Agent 裁决）
- 独立运行 `python -m pytest -q` 与 `python -m ruff check .`
- Phase 1/2/3 spot-check：治理、Hook、`make_plan` 相关测试仍绿
- 对照 prior feedback，不重复实现细节审查
- 核对 README § Skills 与 `.mini-coding-agent/skills/` 模板路径可访问、与实现一致

---

## 交付物

- 回报：[`feedback/P4-REVIEW.md`](../feedback/P4-REVIEW.md)
- 结论：**通过** / **不通过**（含 Blocker 列表）

---

## 验收标准

- [ ] `struct/phase4.md` §3.2 十条 Done Definition 逐项有证据（测试名 / README / 代码路径）
- [ ] §3.3 可靠性契约五项逐项核对
- [ ] README § Skills 与 P4-DOCS 声称无矛盾（spot-check `load_skill`、`--skills`、`/memory`）
- [ ] 仓库内 skills 模板三路径存在且 README 已链接
- [ ] pytest / ruff 独立复验输出附在回报
- [ ] 明确 **Phase 4 当前 in-scope 交付** 可否结项

---

## 参考资料

- [`feedback/P4-SKILLS.md`](../feedback/P4-SKILLS.md)
- [`feedback/P4-DOCS.md`](../feedback/P4-DOCS.md)
- [`struct/phase4.md`](../struct/phase4.md)
- [`feedback/P3-REVIEW.md`](P3-REVIEW.md)（格式参考）

---

*主 Agent 下达*
