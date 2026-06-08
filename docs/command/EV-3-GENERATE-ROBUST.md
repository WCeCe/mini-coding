# EV-3-GENERATE-ROBUST — Generate / 协议鲁棒性

## 元信息

- **TASK_ID**: EV-3-GENERATE-ROBUST
- **TASK_TYPE**: IMPLEMENT
- **优先级**: P0
- **可以写代码**: 是
- **依赖**: EV-1-VERIFY-ALIGN（建议；可与 EV-2 并行）

---

## 目标

针对 live eval 主失败模式，小步增强 **Generate 节点** 与 **`protocol.parse`** 容错，降低 `patch_file` old_text 不匹配、合法 `<tool>` 被误判为 non-tool 的概率。须有 pytest 回归，**不**跳过 governance。

---

## 约束

- 契约：[`struct/eval-repair-plan.md`](../struct/eval-repair-plan.md) §5.3
- 改码范围：`platform/protocol.py`、`modes/graph/nodes/generate.py`（必要时 `platform/tools` patch 校验仅文档化，不大幅改 governance）
- 容错须可测、可逆；禁止「任意 old_text 都匹配」
- 不新增 pip 依赖
- 铁律 §6–§8

---

## 交付物

- 协议 / generate 改动 + pytest（覆盖 GL-5 记录的 fail 模式至少 2 类）
- 可选：`eval/README.md` 补充 live 调参说明
- 回报：[`feedback/EV-3-GENERATE-ROBUST.md`](../feedback/EV-3-GENERATE-ROBUST.md) — **须含**手动 `--live` 复跑摘要（可与 GL-5 表对比）

---

## 验收标准

- [ ] 新增 pytest ≥2 条，对应 `syntaxerror_paren` / `nameerror_greet` 类失败
- [ ] 现有 harness E2E + eval fake 全绿
- [ ] live 复跑记录写入 feedback（不要求 5/5）
- [ ] pytest + ruff 通过

---

## 参考资料

- [`feedback/GL-5-LIVE-EVAL.md`](../feedback/GL-5-LIVE-EVAL.md)
- [`platform/protocol.py`](../../mini_coding_agent/platform/protocol.py)
- [`nodes/generate.py`](../../mini_coding_agent/modes/graph/nodes/generate.py)
