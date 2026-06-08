# Eval 报告

| 任务 | 结果 | failure_type | 失败环节 | 原因 | 耗时(ms) |
|------|------|--------------|----------|------|----------|
| syntaxerror_paren | fail | expect_files | expect_files | calc.py 内容与期望不符 | 46503 |
| nameerror_greet | fail | expect_files | expect_files | greet.py 内容与期望不符 | 51283 |
| missing_return_abs | pass | outcome_ok | — | — | 65263 |
| no_file_hint_add | fail | verify_pytest | verify | pytest 失败（exit 1）：F                                                                        [100%] ================================== FAILURES =================================== __________________________________ test_add ___________________________________      def test_add(): >       assert add(2, 3) == 5 E       assert -1 == 5 E        +  where -1 = add(2, 3)  tests\test_calc.py:4: AssertionError =========================== short test summary info =========================== FAILED tests/test_calc.py::test_add | 50490 |
| bench_retry_off_by_one | pass | pipeline_ok | — | — | 61775 |
| import_chain_rate | pass | locate_wrong_file | — | — | 59633 |
| logic_median_even | pass | outcome_ok | — | — | 91079 |

## Summary

| 指标 | 值 |
|------|-----|
| passed | 4/7 |
| outcome_ok | 4/7 |
| pipeline_ok（有契约任务） | 1/2 |

## 分步结果（失败任务）

- **syntaxerror_paren**：locate:ok → generate:fail → expect_files:fail
- **nameerror_greet**：locate:ok → generate:fail → expect_files:fail
- **no_file_hint_add**：locate:ok → generate:fail → verify:fail

## 架构痛点聚合（failure_type）

| failure_type | 数量 | 任务 |
|--------------|------|------|
| expect_files | 2 | `syntaxerror_paren`, `nameerror_greet` |
| verify_pytest | 1 | `no_file_hint_add` |
| locate_wrong_file | 1 | `import_chain_rate` |

## 建议优先改动

1. `任务设计 / generate` — 2 条 expect_files
2. `nodes/generate.py / nodes/verify.py` — 1 条 verify_pytest
3. `mini_coding_agent/modes/graph/nodes/locate.py` — 1 条 locate_wrong_file

---

## 任务 `syntaxerror_paren` 阶段追踪
### gate

**input**
```
{
  "user_message": "  File \"calc.py\", line 2\n    return (a + b\n              ^\nSyntaxError: '(' was never closed",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\nFile \"calc.py\", line 2\n    return (a + b\n              ^\nSyntaxError: '(' was never closed"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\",\n  \"skill\": null\n}"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-syntaxerror_paren-yjsrovh6\\.mini-coding-agent\\rig.db",
  "files": 1,
  "symbols": 0,
  "imports": 0,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "  File \"calc.py\", line 2\n    return (a + b\n              ^\nSyntaxError: '(' was never closed",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "File \"calc.py\", line 2\n    return (a + b\n              ^\nSyntaxError: '(' was never closed",
  "files_hint": [
    "calc.py"
  ],
  "symbols_hint": []
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "File \"calc.py\", line 2\n    return (a + b\n              ^\nSyntaxError: '(' was never closed",
    "files_hint": [
      "calc.py"
    ],
    "symbols_hint": []
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（hint+search）：1 个文件",
  "files": [
    "calc.py"
  ],
  "snippets": [
    "# file: calc.py L1-L120\n   1: def add(a, b):\n   2:     return (a + b"
  ],
  "used_rig": false,
  "symbols_hint": []
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。\n\n根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，path 固定为 'calc.py'，仅含 new_text。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"calc.py\",\"new_text\":\"…完整替换内容…\"}}</tool>\n\n目标：\nFile \"calc.py\", line 2\n    return (a + b\n              ^\nSyntaxError: '(' was never closed\n\n待替换原文（old_text，系统已确定，勿修改）：\n```\ndef add(a, b):\n    return (a + b\n\n```\n\n定位上下文：\n\n# file: calc.py L1-L120\n   1: def add(a, b):\n   2:     return (a + b",
  "attempt": 0
}
```

**output**
```
{
  "raw": "```json\n<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"calc.py\",\"new_text\":\"def add(a, b):\\n    return (a + b)}}</tool>\n```",
  "ok": false,
  "message": "generate 须返回 tool 调用，收到：```json\n<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"calc.py\",\"new_text\":\"def add(a, b):\\n    return (a + b)}}</tool>\n```"
}
```


---

## 任务 `nameerror_greet` 阶段追踪
### gate

**input**
```
{
  "user_message": "Traceback (most recent call last):\n  File \"greet.py\", line 2, in greet\n    return msg\nNameError: name 'msg' is not defined",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\nTraceback (most recent call last):\n  File \"greet.py\", line 2, in greet\n    return msg\nNameError: name 'msg' is not defined"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\",\n  \"skill\": null\n}"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-nameerror_greet-flireo6t\\.mini-coding-agent\\rig.db",
  "files": 1,
  "symbols": 1,
  "imports": 0,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "Traceback (most recent call last):\n  File \"greet.py\", line 2, in greet\n    return msg\nNameError: name 'msg' is not defined",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "Traceback (most recent call last):\n  File \"greet.py\", line 2, in greet\n    return msg\nNameError: name 'msg' is not defined",
  "files_hint": [
    "greet.py"
  ],
  "symbols_hint": [
    "msg",
    "greet"
  ]
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "Traceback (most recent call last):\n  File \"greet.py\", line 2, in greet\n    return msg\nNameError: name 'msg' is not defined",
    "files_hint": [
      "greet.py"
    ],
    "symbols_hint": [
      "msg",
      "greet"
    ]
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（rig+回退）：1 个文件",
  "files": [
    "greet.py"
  ],
  "snippets": [
    "# search: msg\n# file: greet.py L1-L12\n   1: def greet(name):\n   2:     return msg"
  ],
  "used_rig": true,
  "symbols_hint": [
    "msg",
    "greet"
  ]
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。\n\n根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，path 固定为 'greet.py'，仅含 new_text。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"greet.py\",\"new_text\":\"…完整替换内容…\"}}</tool>\n\n目标：\nTraceback (most recent call last):\n  File \"greet.py\", line 2, in greet\n    return msg\nNameError: name 'msg' is not defined\n\n待替换原文（old_text，系统已确定，勿修改）：\n```\ndef greet(name):\n    return msg\n\n```\n\n定位上下文：\n\n# search: msg\n# file: greet.py L1-L12\n   1: def greet(name):\n   2:     return msg",
  "attempt": 0
}
```

**output**
```
{
  "raw": "<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"greet.py\",\"new_text\":\"def greet(name):\\n    return f'Hello, {name}!'}}</tool>",
  "ok": false,
  "message": "generate 须返回 tool 调用，收到：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"greet.py\",\"new_text\":\"def greet(name):\\n    return f'Hello, {name}!'}}</tool>"
}
```


---

## 任务 `missing_return_abs` 阶段追踪
### gate

**input**
```
{
  "user_message": "pytest 失败：tests/test_abs.py::test_abs — assert abs_val(-3) == 3，实际得到 None",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\npytest 失败：tests/test_abs.py::test_abs — assert abs_val(-3) == 3，实际得到 None"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "```json\n{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\",\n  \"skill\": null\n}\n```"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-missing_return_abs-4wuytufv\\.mini-coding-agent\\rig.db",
  "files": 2,
  "symbols": 2,
  "imports": 1,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "pytest 失败：tests/test_abs.py::test_abs — assert abs_val(-3) == 3，实际得到 None",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "pytest 失败：tests/test_abs.py::test_abs — assert abs_val(-3) == 3，实际得到 None",
  "files_hint": [
    "tests/test_abs.py"
  ],
  "symbols_hint": [],
  "test_command": "python -m pytest -q"
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "pytest 失败：tests/test_abs.py::test_abs — assert abs_val(-3) == 3，实际得到 None",
    "files_hint": [
      "tests/test_abs.py"
    ],
    "symbols_hint": [],
    "test_command": "python -m pytest -q"
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（rig+回退）：2 个文件",
  "files": [
    "tests/test_abs.py",
    "abs_val.py"
  ],
  "snippets": [
    "# rig: test_abs @ tests/test_abs.py:3\n# file: tests/test_abs.py L1-L15\n   1: from abs_val import abs_val\n   2: \n   3: def test_abs():\n   4:     assert abs_val(-3) == 3\n   5:     assert abs_val(5) == 5",
    "# rig: neighbor abs_val.py\n# file: abs_val.py L1-L120\n   1: def abs_val(x):\n   2:     if x < 0:\n   3:         x = -x\n   4:     pass"
  ],
  "used_rig": true,
  "symbols_hint": []
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。\n\n根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，path 固定为 'abs_val.py'，仅含 new_text。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"abs_val.py\",\"new_text\":\"…完整替换内容…\"}}</tool>\n\n目标：\npytest 失败：tests/test_abs.py::test_abs — assert abs_val(-3) == 3，实际得到 None\n\n待替换原文（old_text，系统已确定，勿修改）：\n```\ndef abs_val(x):\n    if x < 0:\n        x = -x\n    pass\n\n```\n\n定位上下文：\n\n# rig: test_abs @ tests/test_abs.py:3\n# file: tests/test_abs.py L1-L15\n   1: from abs_val import abs_val\n   2: \n   3: def test_abs():\n   4:     assert abs_val(-3) == 3\n   5:     assert abs_val(5) == 5\n\n# rig: neighbor abs_val.py\n# file: abs_val.py L1-L120\n   1: def abs_val(x):\n   2:     if x < 0:\n   3:         x = -x\n   4:     pass",
  "attempt": 0
}
```

**output**
```
{
  "raw": "<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"abs_val.py\",\"new_text\":\"def abs_val(x):\\n    if x < 0:\\n        x = -x\\n    return x\\n\"}}",
  "ok": true,
  "message": "已修补 abs_val.py",
  "tool": "patch_file",
  "args": {
    "path": "abs_val.py",
    "old_text": "def abs_val(x):\n    if x < 0:\n        x = -x\n    pass\n",
    "new_text": "def abs_val(x):\n    if x < 0:\n        x = -x\n    return x\n"
  },
  "path": "abs_val.py"
}
```

### verify

**input**
```
{
  "intent_id": "fix_bug",
  "generate_attempt": 0
}
```

**output**
```
{
  "ok": true,
  "message": "exit_code: 0\nstdout:\n.                                                                        [100%]\n1 passed in 0.05s\nstderr:\n（空）",
  "data": {
    "method": "shell",
    "command": "python -m pytest -q"
  }
}
```


---

## 任务 `no_file_hint_add` 阶段追踪
### gate

**input**
```
{
  "user_message": "调用 add(2, 3) 得到 -1，正确结果应为 5。请修复加法实现。",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\n调用 add(2, 3) 得到 -1，正确结果应为 5。请修复加法实现。"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\",\n  \"skill\": null\n}"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-no_file_hint_add-ky9hy5da\\.mini-coding-agent\\rig.db",
  "files": 2,
  "symbols": 2,
  "imports": 1,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "调用 add(2, 3) 得到 -1，正确结果应为 5。请修复加法实现。",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "调用 add(2, 3) 得到 -1，正确结果应为 5。请修复加法实现。",
  "files_hint": [],
  "symbols_hint": [],
  "test_command": "python -m pytest -q"
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "调用 add(2, 3) 得到 -1，正确结果应为 5。请修复加法实现。",
    "files_hint": [],
    "symbols_hint": [],
    "test_command": "python -m pytest -q"
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（hint+search）：0 个文件",
  "files": [],
  "snippets": [],
  "used_rig": false,
  "symbols_hint": []
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。\n\n根据定位上下文，输出唯一一个 <tool> JSON 调用 write_file 或 patch_file 完成目标。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"src/foo.py\",\"old_text\":\"bad\",\"new_text\":\"good\"}}</tool>\n\n目标：\n调用 add(2, 3) 得到 -1，正确结果应为 5。请修复加法实现。\n\n定位上下文：\n\n（无定位上下文）",
  "attempt": 0
}
```

**output**
```
{
  "raw": "<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"src/foo.py\",\"old_text\":\"def add(a, b):\\n    return a + b\",\"new_text\":\"def add(a, b):\\n    return a - b\"}}</tool>",
  "ok": false,
  "message": "错误：patch_file 参数无效：path 不是文件\n示例：<tool name=\"patch_file\" path=\"binary_search.py\"><old_text>return -1</old_text><new_text>return mid</new_text></tool>",
  "tool": "patch_file",
  "args": {
    "path": "src/foo.py",
    "old_text": "def add(a, b):\n    return a + b",
    "new_text": "def add(a, b):\n    return a - b"
  },
  "path": "src/foo.py"
}
```


---

## 任务 `bench_retry_off_by_one` 阶段追踪
### gate

**input**
```
{
  "user_message": "pytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\npytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\"\n}"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-bench_retry_off_by_one-6mc4rye8\\.mini-coding-agent\\rig.db",
  "files": 2,
  "symbols": 2,
  "imports": 1,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "pytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "pytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3",
  "files_hint": [
    "tests/test_sum.py"
  ],
  "symbols_hint": [],
  "test_command": "python -m pytest -q"
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "pytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3",
    "files_hint": [
      "tests/test_sum.py"
    ],
    "symbols_hint": [],
    "test_command": "python -m pytest -q"
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（rig+回退）：2 个文件",
  "files": [
    "tests/test_sum.py",
    "sum_first.py"
  ],
  "snippets": [
    "# rig: test_sum_first @ tests/test_sum.py:3\n# file: tests/test_sum.py L1-L14\n   1: from sum_first import sum_first\n   2: \n   3: def test_sum_first():\n   4:     assert sum_first(3) == 6",
    "# rig: neighbor sum_first.py\n# file: sum_first.py L1-L120\n   1: def sum_first(n):\n   2:     s = 0\n   3:     for i in range(1, n):\n   4:         s += i\n   5:     return s"
  ],
  "used_rig": true,
  "symbols_hint": []
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。\n\n根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，path 固定为 'sum_first.py'，仅含 new_text。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"sum_first.py\",\"new_text\":\"…完整替换内容…\"}}</tool>\n\n目标：\npytest 失败：tests/test_sum.py::test_sum_first — assert sum_first(3) == 6，实际得到 3\n\n待替换原文（old_text，系统已确定，勿修改）：\n```\ndef sum_first(n):\n    s = 0\n    for i in range(1, n):\n        s += i\n    return s\n\n```\n\n定位上下文：\n\n# rig: test_sum_first @ tests/test_sum.py:3\n# file: tests/test_sum.py L1-L14\n   1: from sum_first import sum_first\n   2: \n   3: def test_sum_first():\n   4:     assert sum_first(3) == 6\n\n# rig: neighbor sum_first.py\n# file: sum_first.py L1-L120\n   1: def sum_first(n):\n   2:     s = 0\n   3:     for i in range(1, n):\n   4:         s += i\n   5:     return s",
  "attempt": 0
}
```

**output**
```
{
  "raw": "```\ndef sum_first(n):\n    s = 0\n    for i in range(1, n + 1):\n        s += i\n    return s\n```",
  "ok": true,
  "message": "已修补 sum_first.py",
  "tool": "patch_file",
  "args": {
    "path": "sum_first.py",
    "old_text": "def sum_first(n):\n    s = 0\n    for i in range(1, n):\n        s += i\n    return s\n",
    "new_text": "def sum_first(n):\n    s = 0\n    for i in range(1, n + 1):\n        s += i\n    return s"
  },
  "path": "sum_first.py"
}
```

### verify

**input**
```
{
  "intent_id": "fix_bug",
  "generate_attempt": 0
}
```

**output**
```
{
  "ok": true,
  "message": "exit_code: 0\nstdout:\n.                                                                        [100%]\n1 passed in 0.03s\nstderr:\n（空）",
  "data": {
    "method": "shell",
    "command": "python -m pytest -q"
  }
}
```


---

## 任务 `import_chain_rate` 阶段追踪
### gate

**input**
```
{
  "user_message": "pytest 失败：tests/test_compute.py::test_compute — assert compute() == 20，实际 2000。百分比费率计算有误。",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\npytest 失败：tests/test_compute.py::test_compute — assert compute() == 20，实际 2000。百分比费率计算有误。"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "```json\n{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\",\n  \"skill\": null\n}\n```"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-import_chain_rate-f0_7o6x6\\.mini-coding-agent\\rig.db",
  "files": 3,
  "symbols": 3,
  "imports": 2,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "pytest 失败：tests/test_compute.py::test_compute — assert compute() == 20，实际 2000。百分比费率计算有误。",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "pytest 失败：tests/test_compute.py::test_compute — assert compute() == 20，实际 2000。百分比费率计算有误。",
  "files_hint": [
    "tests/test_compute.py"
  ],
  "symbols_hint": [],
  "test_command": "python -m pytest -q"
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "pytest 失败：tests/test_compute.py::test_compute — assert compute() == 20，实际 2000。百分比费率计算有误。",
    "files_hint": [
      "tests/test_compute.py"
    ],
    "symbols_hint": [],
    "test_command": "python -m pytest -q"
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（rig+回退）：2 个文件",
  "files": [
    "tests/test_compute.py",
    "app.py"
  ],
  "snippets": [
    "# rig: test_compute @ tests/test_compute.py:3\n# file: tests/test_compute.py L1-L14\n   1: from app import compute\n   2: \n   3: def test_compute():\n   4:     assert compute() == 20",
    "# rig: neighbor app.py\n# file: app.py L1-L120\n   1: from rates import apply_rate\n   2: \n   3: def compute():\n   4:     return apply_rate(200, 10)"
  ],
  "used_rig": true,
  "symbols_hint": []
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。\n\n根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，path 固定为 'app.py'，仅含 new_text。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"app.py\",\"new_text\":\"…完整替换内容…\"}}</tool>\n\n目标：\npytest 失败：tests/test_compute.py::test_compute — assert compute() == 20，实际 2000。百分比费率计算有误。\n\n待替换原文（old_text，系统已确定，勿修改）：\n```\nfrom rates import apply_rate\n\ndef compute():\n    return apply_rate(200, 10)\n\n```\n\n定位上下文：\n\n# rig: test_compute @ tests/test_compute.py:3\n# file: tests/test_compute.py L1-L14\n   1: from app import compute\n   2: \n   3: def test_compute():\n   4:     assert compute() == 20\n\n# rig: neighbor app.py\n# file: app.py L1-L120\n   1: from rates import apply_rate\n   2: \n   3: def compute():\n   4:     return apply_rate(200, 10)",
  "attempt": 0
}
```

**output**
```
{
  "raw": "```\nfrom rates import apply_rate\n\ndef compute():\n    return apply_rate(200, 0.1)\n```",
  "ok": true,
  "message": "已修补 app.py",
  "tool": "patch_file",
  "args": {
    "path": "app.py",
    "old_text": "from rates import apply_rate\n\ndef compute():\n    return apply_rate(200, 10)\n",
    "new_text": "from rates import apply_rate\n\ndef compute():\n    return apply_rate(200, 0.1)"
  },
  "path": "app.py"
}
```

### verify

**input**
```
{
  "intent_id": "fix_bug",
  "generate_attempt": 0
}
```

**output**
```
{
  "ok": true,
  "message": "exit_code: 0\nstdout:\n.                                                                        [100%]\n1 passed in 0.06s\nstderr:\n（空）",
  "data": {
    "method": "shell",
    "command": "python -m pytest -q"
  }
}
```


---

## 任务 `logic_median_even` 阶段追踪
### gate

**input**
```
{
  "user_message": "pytest 失败：tests/test_stats.py::test_median_even — assert median([1,2,3,4]) == 2.5，实际 3。偶数长度列表的中位数计算有误。",
  "prompt": "你是 Mini-Coding-Agent 的意图分类器（Gate）。\n\n根据用户消息，将其归入下列五类意图之一；仅回复一个 JSON 对象（不要用 markdown 围栏，不要附加说明）。\n\nJSON 字段名必须为英文，说明性文字可用中文。\n\n{\n  \"intent_id\": \"generate_code | fix_bug | refactor | explain | project_ops\",\n  \"confidence\": \"high | low\",\n  \"skill\": \"null 或 skill 名字符串（可选）\"\n}\n\n五类意图（intent_id 必须精确使用下列英文 id）：\n\n| intent_id | 含义 | 典型用户话 |\n|-----------|------|------------|\n| generate_code | 新增/实现代码：新文件、新函数、加测试、按需求写功能 | 「实现一个…」「加个模块」「写单元测试」 |\n| fix_bug | 修复错误：traceback、测试挂、行为不对 | 「报错」「修 bug」「测试失败」 |\n| refactor | 不改语义前提下改结构：重命名、抽函数、整理目录 | 「重构」「提取公共逻辑」 |\n| explain | 只理解不改码：解释、阅读、梳理调用 | 「什么意思」「怎么工作的」「解释一下」 |\n| project_ops | 项目操作：装依赖、跑测试/脚本、git 状态（非改源码） | 「跑 pytest」「pip install」「git status」 |\n\n边界示例（减少混类）：\n\n1. 中英混杂 · 又要改又要解释：「explain how login works and fix the bug in auth.py」\n   → 要改文件 → fix_bug（不是 explain）\n\n2. 中英混杂 · 只跑不改：「please run pytest for me, 不用改代码」\n   → project_ops（不是 fix_bug）\n\n3. 「写测试」：新测试文件/大量新增 → generate_code；测试挂了要修 → fix_bug\n\n4. 「跑一下测试」不改码 → project_ops\n\n5. 意图跨多类且无法确定主目标 → confidence=low\n\n规则：\n\n- confidence=high：意图明确、可归入上述五类之一。\n\n- confidence=low：意图含糊、跨多类、或无法判断是否要改代码。\n\n- skill：若用户明确点名某 Skill 名可填字符串，否则 null。\n\n用户消息：\npytest 失败：tests/test_stats.py::test_median_even — assert median([1,2,3,4]) == 2.5，实际 3。偶数长度列表的中位数计算有误。"
}
```

**output**
```
{
  "intent_id": "fix_bug",
  "confidence": "high",
  "route": "harness_pipeline",
  "raw": "{\n  \"intent_id\": \"fix_bug\",\n  \"confidence\": \"high\",\n  \"skill\": null\n}"
}
```

### rig

**output**
```
{
  "db_path": "C:\\Users\\hspcadmin\\AppData\\Local\\Temp\\eval-logic_median_even-k6phzhx3\\.mini-coding-agent\\rig.db",
  "files": 2,
  "symbols": 3,
  "imports": 1,
  "built": true
}
```

### slots

**input**
```
{
  "user_message": "pytest 失败：tests/test_stats.py::test_median_even — assert median([1,2,3,4]) == 2.5，实际 3。偶数长度列表的中位数计算有误。",
  "intent_id": "fix_bug"
}
```

**output**
```
{
  "goal": "pytest 失败：tests/test_stats.py::test_median_even — assert median([1,2,3,4]) == 2.5，实际 3。偶数长度列表的中位数计算有误。",
  "files_hint": [
    "tests/test_stats.py"
  ],
  "symbols_hint": [],
  "test_command": "python -m pytest -q"
}
```

### locate

**input**
```
{
  "slots": {
    "goal": "pytest 失败：tests/test_stats.py::test_median_even — assert median([1,2,3,4]) == 2.5，实际 3。偶数长度列表的中位数计算有误。",
    "files_hint": [
      "tests/test_stats.py"
    ],
    "symbols_hint": [],
    "test_command": "python -m pytest -q"
  }
}
```

**output**
```
{
  "ok": true,
  "message": "定位完成（rig+回退）：2 个文件",
  "files": [
    "tests/test_stats.py",
    "stats.py"
  ],
  "snippets": [
    "# rig: test_median_odd @ tests/test_stats.py:3\n# file: tests/test_stats.py L1-L14\n   1: from stats import median\n   2: \n   3: def test_median_odd():\n   4:     assert median([1, 3, 5]) == 3\n   5: \n   6: def test_median_even():\n   7:     assert median([1, 2, 3, 4]) == 2.5",
    "# rig: test_median_even @ tests/test_stats.py:6\n# file: tests/test_stats.py L1-L17\n   1: from stats import median\n   2: \n   3: def test_median_odd():\n   4:     assert median([1, 3, 5]) == 3\n   5: \n   6: def test_median_even():\n   7:     assert median([1, 2, 3, 4]) == 2.5",
    "# rig: neighbor stats.py\n# file: stats.py L1-L120\n   1: def median(nums):\n   2:     ordered = sorted(nums)\n   3:     mid = len(ordered) // 2\n   4:     return ordered[mid]"
  ],
  "used_rig": true,
  "symbols_hint": []
}
```

### generate
- meta: `{"intent_id": "fix_bug"}`

**input**
```
{
  "prompt": "你是 Mini-Coding-Agent 的代码生成节点。\n\n当前意图：fix_bug。偏向修复 traceback/测试失败。禁止 write_file/patch_file 修改 tests/ 下任何文件，只改源码。系统已从磁盘读取 old_text（见下方「待替换原文」），你只需输出 new_text 作为完整替换内容（含缩进）。调用 patch_file 时 args 仅含 path 与 new_text，不要输出 old_text。\n\n根据下方待替换原文，输出唯一一个 <tool> JSON 调用 patch_file，path 固定为 'stats.py'，仅含 new_text。\n\n不要输出 <final>；不要调用其他工具。\n\n示例：<tool>{\"name\":\"patch_file\",\"args\":{\"path\":\"stats.py\",\"new_text\":\"…完整替换内容…\"}}</tool>\n\n目标：\npytest 失败：tests/test_stats.py::test_median_even — assert median([1,2,3,4]) == 2.5，实际 3。偶数长度列表的中位数计算有误。\n\n待替换原文（old_text，系统已确定，勿修改）：\n```\ndef median(nums):\n    ordered = sorted(nums)\n    mid = len(ordered) // 2\n    return ordered[mid]\n\n```\n\n定位上下文：\n\n# rig: test_median_odd @ tests/test_stats.py:3\n# file: tests/test_stats.py L1-L14\n   1: from stats import median\n   2: \n   3: def test_median_odd():\n   4:     assert median([1, 3, 5]) == 3\n   5: \n   6: def test_median_even():\n   7:     assert median([1, 2, 3, 4]) == 2.5\n\n# rig: test_median_even @ tests/test_stats.py:6\n# file: tests/test_stats.py L1-L17\n   1: from stats import median\n   2: \n   3: def test_median_odd():\n   4:     assert median([1, 3, 5]) == 3\n   5: \n   6: def test_median_even():\n   7:     assert median([1, 2, 3, 4]) == 2.5\n\n# rig: neighbor stats.py\n# file: stats.py L1-L120\n   1: def median(nums):\n   2:     ordered = sorted(nums)\n   3:     mid = len(ordered) // 2\n   4:     return ordered[mid]",
  "attempt": 0
}
```

**output**
```
{
  "raw": "```\ndef median(nums):\n    ordered = sorted(nums)\n    n = len(ordered)\n    if n % 2 == 0:\n        return (ordered[n//2 - 1] + ordered[n//2]) / 2\n    else:\n        return ordered[n//2]\n```",
  "ok": true,
  "message": "已修补 stats.py",
  "tool": "patch_file",
  "args": {
    "path": "stats.py",
    "old_text": "def median(nums):\n    ordered = sorted(nums)\n    mid = len(ordered) // 2\n    return ordered[mid]\n",
    "new_text": "def median(nums):\n    ordered = sorted(nums)\n    n = len(ordered)\n    if n % 2 == 0:\n        return (ordered[n//2 - 1] + ordered[n//2]) / 2\n    else:\n        return ordered[n//2]"
  },
  "path": "stats.py"
}
```

### verify

**input**
```
{
  "intent_id": "fix_bug",
  "generate_attempt": 0
}
```

**output**
```
{
  "ok": true,
  "message": "exit_code: 0\nstdout:\n..                                                                       [100%]\n2 passed in 0.06s\nstderr:\n（空）",
  "data": {
    "method": "shell",
    "command": "python -m pytest -q"
  }
}
```

