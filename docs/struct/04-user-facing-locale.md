# 用户可见文案规范（中文）

> **铁律摘要**：见 [`01-vision-and-roadmap.md`](./01-vision-and-roadmap.md) §8。  
> Mini-Coding-Agent 面向中文用户；**运行时与 prompt 中面向人或模型的说明性文字用中文**，**协议与代码标识保持英文**。

---

## 1. 适用范围（须中文）

| 类别 | 示例位置 |
|------|----------|
| Agent 主 prompt | `build_prefix` 规则、`prompt()` 分段标题（规则/工具/记忆/对话记录/当前用户请求） |
| 任务规划 | `planning.build_planning_prompt`、`validate_plan` 的 `ValueError` |
| 工具说明 | `build_tools()` 中各工具的 `description`；风险标签 `需审批` / `安全` |
| 工具返回 | 成功（`已写入`、`已修补`、`规划成功`）、失败（`错误：…`）、`retry_notice` |
| 参数校验 | `validate_tool` / `tool_*` 抛出的 `ValueError` 文案 |
| 门控与审批 | `--plan-first` 拒绝提示、`approve()` 的终端问句、diff 预览标题 |
| Session 记忆展示 | `memory_text()`、`history_text()` 空状态等 |
| 工作区快照 | `WorkspaceContext.text()` 顶层标题（字段名仍可英文，见 §2） |
| CLI | `argparse` 的 `description` / `help`、`/help` 内容（`constants.HELP_DETAILS`） |
| Hook / 模型 | trace 行、shell 审计行、`hooks.yaml` 配置警告、`OllamaModelClient` 面向用户的 `RuntimeError` |
| REPL 反馈 | `会话已重置`、`ask()` 步数用尽等停止说明 |

**新增或修改上述文案时**：用中文撰写；**同步更新** `tests/` 中相关断言。

---

## 2. 保留英文（勿翻译）

| 类别 | 说明 |
|------|------|
| **工具名** | `read_file`、`write_file`、`make_plan`、`delegate` 等 |
| **参数名** | `goal`、`path`、`old_text`、`context`、`timeout` 等 |
| **JSON 字段名** | plan 的 `goal`、`steps`、`id`、`title`、`acceptance`、`assumptions`、`out_of_scope` |
| **协议标签与格式** | `<tool>`、`<final>`、`<plan_json>`；tool JSON/XML 调用示例中的 `name` / `args` |
| **CLI 旗标** | `--plan-first`、`--approval` 等（help 正文用中文解释即可） |
| **技术输出字段** | `run_shell` 返回中的 `exit_code:`、`stdout:`、`stderr:` |
| **代码标识** | 模块名、类名、函数名、变量名、文件名 |
| **Unified diff 体** | `--- a/`、`+++ b/` 及 diff 正文（标准格式） |

规划类 JSON：**字段名英文，字段值建议中文**（专有名词除外）。

---

## 3. 错误与成功前缀（统一）

| 类型 | 前缀 / 格式 |
|------|-------------|
| 工具/运行时错误 | `错误：`（首选）；`util.tool_result_success` 同时识别 `error:` 以兼容旧记录 |
| 参数无效 | `错误：{tool} 参数无效：{原因}`，可附 `示例：{tool_example}` |
| 规划失败 | `错误：make_plan 失败：{原因}` |
| 规划成功 | `规划成功` + 摘要 + `<plan_json>…</plan_json>` |
| 写文件成功 | `已写入 {path}（{n} 字符）` |
| 修补成功 | `已修补 {path}` |
| 重试提示 | `运行时提示：…` + 说明有效的 `<tool>` / `<final>` |

校验类 `ValueError` 应写清**哪个参数/字段**有问题，例如：`参数 goal 不能为空`、`路径超出工作区：{path}`。

---

## 4. 与文档、测试的关系

| 文档类型 | 语言 |
|----------|------|
| `struct/`、`command/`、`feedback/` | 中文为主 |
| 根目录 `README.md` | 可为英文产品说明；与代码行为矛盾时**以代码与本规范为准** |
| pytest | 断言须匹配当前中文文案；勿为通过测试而改回英文运行时字符串 |

---

## 5. 子 Agent / 主 Agent 检查清单

实现或改文案前自检：

- [ ] 用户能直接看到的字符串是否已为中文？
- [ ] 工具名、参数名、JSON 字段、`<tool>` 协议是否仍为英文？
- [ ] 新增 `错误：` / `规划成功` 等是否已更新测试？
- [ ] 是否误删用户注释（铁律 §6）？

---

*struct/04-user-facing-locale · 与 `mini_coding_agent/` 全包汉化实现对齐*
