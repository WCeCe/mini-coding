# Phase 1 调研清单（用户向）

> 根据 [`struct/01-vision-and-roadmap.md`](../../struct/01-vision-and-roadmap.md) 与 [`struct/phase1.md`](../../struct/phase1.md) 进行调研。
>
> **你的笔记请写在同目录下**（如 `Aider.md`），不要写进 `struct/` 或 `feedback/`。

四个决策已对齐（2026-05-29）；本清单用于**加深理解**，为评审实现设计稿和面试叙述服务。

---

## 1. 调研检查项

### 1.1 变更如何表示

- [ ] unified diff 格式；Python `difflib.unified_diff` 用法
- [ ] 整文件替换 vs search/replace vs unified diff hunk 的优缺点
- [ ] 模型输出哪种更稳；人 review 哪种更清晰

### 1.2 变更如何应用

- [ ] patch 前如何校验路径、hunk 上下文
- [ ] 本项目 `patch_file`（old_text 唯一）与 Aider SEARCH/REPLACE 的异同
- [ ] 新建 / 修改 / 删除是否应统一流程

### 1.3 回滚与 checkpoint

- [ ] 回滚粒度：单次 tool / 单次 ask / 整个 session
- [ ] snapshot 存放：`.mini-coding-agent/checkpoints/` vs `git stash`
- [ ] 回滚失败时的降级策略

### 1.4 审批与人机协作

- [ ] 「approve diff」与现有 `approve` 的交互差异
- [ ] 终端 diff 展示（截断、颜色）
- [ ] 拒绝后给模型的反馈形式

### 1.5 Git 集成

- [ ] 只读 `git diff` / `status` 是否够用
- [ ] 工作区不干净时 agent 改文件的风险

---

## 2. 参考对象

| 参考 | 重点 |
|------|------|
| [Aider](https://aider.chat) | diff 编辑、SEARCH/REPLACE、git、拒绝时磁盘状态 |
| 本项目 `mini_coding_agent.py` | `write_file` / `patch_file` / `approve` 链路 |
| `difflib` 文档 | unified diff 格式 |
| OpenHands / SWE-agent | 第二阶段参考，第一版了解即可 |

### 阅读 Aider 时建议回答

1. 变更在哪一步从「计划」变成「落盘」？
2. 用户拒绝编辑时，磁盘变了吗？
3. 回滚靠内部 backup 还是 git？
4. SEARCH/REPLACE 失败时，给模型什么反馈？

---

## 3. 建议阅读顺序

1. Aider 文档 / 源码（变更与 git 相关部分）
2. 本地用 `difflib` 生成一个小文件 diff
3. 对照 [`min_agent的变更代码逻辑.md`](./min_agent的变更代码逻辑.md) 走读本项目
4. 阅读 [`struct/phase1.md`](../../struct/phase1.md)，标注同意 / 疑问

---

## 4. 笔记文末建议格式

```markdown
## 结论摘要
- ...

## 对 struct/05 设计稿的意见
- 同意 / 建议修改：...

## 面试可讲的一点
- ...
```

---

*调研清单 · 主 Agent 维护 · 用户笔记在同目录自由扩展*
