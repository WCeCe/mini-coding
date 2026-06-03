import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from mini_coding_agent.constants import IGNORED_PATH_NAMES, MAX_HISTORY
from mini_coding_agent.planning import (
    build_planning_prompt,
    format_plan_tool_result,
    parse_plan_response,
    plan_summary_text,
)
from mini_coding_agent.skills import (
    SkillCatalog,
    emit_skill_warnings,
    format_load_skill_result,
    loaded_skills_summary,
)
from mini_coding_agent.hooks.hook_config import default_hook_config, emit_config_warnings, load_hook_config
from mini_coding_agent.hooks import HookRegistry, ToolHookContext, register_builtin_hooks
from mini_coding_agent.session import CheckpointStore
from mini_coding_agent.util import (
    atomic_write_text,
    build_unified_diff,
    clip,
    diff_summary,
    file_sha256,
    now,
    text_sha256,
    tool_result_success,
)


class MiniAgent:
    def __init__(
        self,
        model_client,
        workspace,
        session_store,
        session=None,
        #危险工具是否使用的三种策略：ask每次都询问；auto全部批准；never全部拒绝
        approval_policy="ask",
        max_steps=6,
        max_new_tokens=512,
        depth=0,
        max_depth=1,
        read_only=False,
        enable_trace_hook=True,
        hook_config=None,
        # Phase 3: CLI --plan-first；是否需要先plan
        plan_first=False,
        # Phase 4: CLI --skills 预加载的 skill 名列表
        preload_skills=None,
    ):
        self.model_client = model_client
        self.workspace = workspace
        self.root = Path(workspace.repo_root)
        self.session_store = session_store
        self.approval_policy = approval_policy
        self.max_steps = max_steps
        self.max_new_tokens = max_new_tokens
        self.depth = depth
        self.max_depth = max_depth
        self.read_only = read_only
        self.plan_first = plan_first
        self.preload_skills = list(preload_skills or [])
        # Phase 4: 启动/resume 时扫描 skills 目录（目录缺失不 fatal）
        self.skill_catalog, skill_scan_warnings = SkillCatalog.scan(self.root)
        emit_skill_warnings(skill_scan_warnings)
        # 首先要是在--plan_first的命令前提下，如果_ask_plan_satisfied为false，就禁止使用写等危险操作
        #只能读或者是执行plan，在plan后会将其改为true，此时就允许危险操作了。
        self._ask_plan_satisfied = False
        # Phase 2: 工具边界 Hook 注册表；YAML + 内置 Hook 栈
        self.hook_registry = HookRegistry()
        if enable_trace_hook:
            if hook_config is None:
                config_path = self.root / ".mini-coding-agent" / "hooks.yaml"
                hook_config, config_warnings = load_hook_config(config_path)
                emit_config_warnings(config_warnings)
            self.hook_config = hook_config
            register_builtin_hooks(self.hook_registry, hook_config)
        else:
            # 测试隔离：关闭全部内置 Hook
            self.hook_config = default_hook_config()
            self.hook_config.session_trace = False
            self.hook_config.trace_display = False
            self.hook_config.shell_audit = False
        self.checkpoint_store = CheckpointStore(self.root / ".mini-coding-agent" / "checkpoints")
        #是「上一次文件写操作」的治理附加信息（diff 摘要、checkpoint id、是否回滚）
        self._last_tool_meta = {}
        #如果没有旧会话，则初始化session
        self.session = session or {
            "id": datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6],
            "created_at": now(),
            "workspace_root": workspace.repo_root,
            #历史是纯对话文本，不压缩删减等
            "history": [],
            #简短的记录任务、文件、备注
            #files只存文件相关的操作tool
            #notes是最近所有操作，包括final的结果
            # plan: Phase 3 成功的make_plan 的结构化 JSON（dict 或 None）
            # loaded_skills: Phase 4 已加载 Skill 正文（name -> {name, description, body}）
            "memory": {"task": "", "files": [], "notes": [], "plan": None, "loaded_skills": {}},
        }
        self._ensure_memory_shape()
        # Phase 4: CLI --skills 预加载（未知名 warn，已知项仍加载）
        preload_warnings = self._preload_skills(self.preload_skills)
        emit_skill_warnings(preload_warnings)
        #构建tools
        self.tools = self.build_tools()
        #构建prompt的prefix部分
        self.prefix = self.build_prefix()
        #先进行一次初始化，写到磁盘中
        self.session_path = self.session_store.save(self.session)

    @classmethod
    #**kwargs省略了一些参数，因为有默认值
    #from_session方法，语法糖，其实也是重新构建该Agent对象
    def from_session(cls, model_client, workspace, session_store, session_id, **kwargs):
        return cls(
            model_client=model_client,
            workspace=workspace,
            session_store=session_store,
            session=session_store.load(session_id),
            **kwargs,
        )

    #对memory的三个bucket进行存储
    @staticmethod
    def remember(bucket, item, limit):
        if not item:
            return
        #该文件已经存在，则删除
        if item in bucket:
            bucket.remove(item)
        #整体再添加，最新的放到最后面
        bucket.append(item)
        #超过8个，删除最老的，也就是最前面的
        del bucket[:-limit]

    ###############################################
    #### 3) Structured Tools And Permissions ######
    ###############################################
    #搭建tools字典
    def build_tools(self):
        tools = {
            "list_files": {
                "schema": {"path": "str='.'"},
                "risky": False,
                "description": "列出工作区中的文件与目录。",
                "run": self.tool_list_files,
            },
            #有大小限制
            "read_file": {
                "schema": {"path": "str", "start": "int=1", "end": "int=200"},
                "risky": False,
                "description": "按行范围读取 UTF-8 文本文件。",
                "run": self.tool_read_file,
            },
            #pattern要在代码/文件里查找的文字
            "search": {
                "schema": {"pattern": "str", "path": "str='.'"},
                "risky": False,
                "description": "在工作区中搜索（优先 rg，否则简单回退）。",
                "run": self.tool_search,
            },
            #command要执行的命令
            "run_shell": {
                "schema": {"command": "str", "timeout": "int=20"},
                "risky": True,
                "description": "在仓库根目录执行 shell 命令。",
                "run": self.tool_run_shell,
            },
            #content要写入的文本内容
            "write_file": {
                "schema": {"path": "str", "content": "str"},
                "risky": True,
                "description": "写入文本文件。",
                "run": self.tool_write_file,
            },
            #精确文本替换，old_text源文本中要被替换的那一段，new_text要替换的
            "patch_file": {
                "schema": {"path": "str", "old_text": "str", "new_text": "str"},
                "risky": True,
                "description": "在文件中精确替换一段文本。",
                "run": self.tool_patch_file,
            },
            # Phase 3: 单次 complete 产出任务级计划（无内部 tool 循环）；全 depth 注册
            # 与 delegate 区别：delegate=子 Agent 多步只读调查，仅 depth<max_depth；make_plan=本层一次规划
            "make_plan": {
                "schema": {"goal": "str", "context": "str=''"},
                "risky": False,
                "description": "生成结构化任务级计划（单次 make_plan 调用，无内部 tool 循环）。",
                "run": self.tool_make_plan,
            },
            # Phase 4: 按需加载 Skill 正文到 session memory（safe；observe-only）
            "load_skill": {
                "schema": {"name": "str"},
                "risky": False,
                "description": "加载仓库 Skill 正文到 session memory（启动时 prefix 仅含 metadata 清单）。",
                "run": self.tool_load_skill,
            },
        }
        #max_depth为1，只允许调用一层子Agent，子Agent不能继续往下调用；且子Agent只读
        if self.depth < self.max_depth:
            tools["delegate"] = {
                "schema": {"task": "str", "max_steps": "int=3"},
                "risky": False,
                "description": "调用有界只读子 Agent 进行调查。",
                "run": self.tool_delegate,
            }
        return tools

    ############################################
    #### 2) Prompt Shape And Cache Reuse #######
    ############################################
    #构建prompt的prefix部分，同一次Agent生命周期内 基本不变
    def build_prefix(self):
        tool_lines = []
        for name, tool in self.tools.items():
            #获取工具的参数path、start啥的
            fields = ", ".join(f"{key}: {value}" for key, value in tool["schema"].items())
            #获取风险
            risk = "需审批" if tool["risky"] else "安全"
            #写成这样的形式：tool_lines.append("- read_file(path: str, start: int=1, end: int=200) [safe] Read a UTF-8 file by line range.")
            tool_lines.append(f"- {name}({fields}) [{risk}] {tool['description']}")
        #1.工具列表
        tool_text = "\n".join(tool_lines)
        #2，这是模型该怎么输出的例子
        examples = "\n".join(
            [
                '<tool>{"name":"list_files","args":{"path":"."}}</tool>',
                '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":80}}</tool>',
                '<tool name="write_file" path="binary_search.py"><content>def binary_search(nums, target):\n    return -1\n</content></tool>',
                '<tool name="patch_file" path="binary_search.py"><old_text>return -1</old_text><new_text>return mid</new_text></tool>',
                '<tool>{"name":"run_shell","args":{"command":"uv run --with pytest python -m pytest -q","timeout":20}}</tool>',
                '<tool>{"name":"make_plan","args":{"goal":"add tests for module X","context":"read README first"}}</tool>',
                '<tool>{"name":"load_skill","args":{"name":"code-review"}}</tool>',
                "<final>Done.</final>",
            ]
        )
        #3.规则
        rules = "\n".join([
            "- 不要猜测工作区内容，请使用工具获取事实。",
            "- 每次只返回一个 <tool>...</tool> 或一个 <final>...</final>。",
            "- tool 调用格式示例：",
            '  <tool>{"name":"tool_name","args":{...}}</tool>',
            "- write_file、patch_file 的多行内容优先使用 XML 格式：",
            '  <tool name="write_file" path="file.py"><content>...</content></tool>',
            "- 最终回答格式：",
            "  <final>你的回答</final>",
            "- 不要编造工具执行结果。",
            "- 回答简洁、具体。",
            "- 用户要求创建或更新明确路径的文件时，用 write_file 或 patch_file，不要反复 list_files。",
            "- 为现有代码写测试前，先 read_file 阅读实现。",
            "- 写测试时匹配当前实现，除非用户明确要求改代码。",
            "- 新建文件应完整可运行，包含必要 import。",
            "- 同一参数重复调用无效工具时，换工具或返回 <final>。",
            "- 必填工具参数不能为空。不得用空 args 调用 read_file、write_file、patch_file、run_shell、delegate、make_plan、load_skill。",
            "- 多文件改动、需求含糊或用户要求规划时：先用 read_file/search 调查，再 make_plan，再执行 risky 工具（write_file、patch_file、run_shell）。",
            "- delegate = 有界只读子 Agent 调查；make_plan = 单次结构化任务拆分（不能替代 delegate）。",
        ])
        # Phase 4: 阶段一 Skill metadata 清单（不含 SKILL.md 正文）
        skills_text = self.skill_catalog.metadata_block()
        #构建prompt的prefix部分，prefix又分为五个部分：
        #1.You are Mini-Coding-Agent...
        #2. 规则：Rules: + rules
        #3. 工具列表：Tools: + tool_lines
        #4. 案例：Valid response examples: + examples
        #5. 仓库快照：workspace.text()（仓库快照）
        return "\n\n".join([
            "你是 Mini-Coding-Agent，通过 Ollama 运行的本地小型编程 Agent。",
            "规则：\n" + rules,
            "工具：\n" + tool_text,
            "有效响应示例：\n" + examples,
            skills_text,
            self.workspace.text(),
        ])

    #构建memory（含 Phase 3 plan 摘要，会进入 prompt() 供模型对照执行）
    def memory_text(self):
        memory = self.session["memory"]
        notes = "\n".join(f"- {note}" for note in memory["notes"]) or "- 无"
        plan = memory.get("plan")
        if plan:
            plan_lines = plan_summary_text(plan).splitlines()
            plan_block = "\n".join(f"  {line}" for line in plan_lines)
        else:
            plan_block = "  - 无"
        # Phase 4: 已加载 Skill 摘要 + 正文（进入后续 prompt）
        loaded = memory.get("loaded_skills") or {}
        loaded_lines = [loaded_skills_summary(loaded)]
        for skill_name in sorted(loaded.keys()):
            item = loaded[skill_name]
            if isinstance(item, dict) and item.get("body"):
                body = str(item["body"]).strip()
                loaded_lines.append(f"  [{skill_name} 正文]\n{body}")
        loaded_block = "\n".join(loaded_lines)
        return "\n".join([
            "记忆：",
            f"- task: {memory['task'] or '-'}",
            f"- files: {', '.join(memory['files']) or '-'}",
            "- plan:",
            plan_block,
            "- loaded_skills:",
            loaded_block,
            "- notes:",
            notes,
        ])

    #####################################################
    #### 4) Context Reduction And Output Management #####
    #####################################################
    #获取历史信息
    def history_text(self):
        history = self.session["history"]
        if not history:
            return "- （空）"
        #存储格式化后的历史文本行，用于最终拼接输出
        lines = []
        #只针对非最近（较旧）的 read_file 工具调用
        #例如：历史中出现了三次对 /etc/config 的旧读取记录，最终只输出第一条。这样可以避免历史文本中出现大量重复的读取内容，节省空间。
        seen_reads = set()
        recent_start = max(0, len(history) - 6)
        for index, item in enumerate(history):
            #recent是bool变量，来区分旧和新
            recent = index >= recent_start
            if item["role"] == "tool" and item["name"] in ("write_file", "patch_file"):
                path = str(item["args"].get("path", ""))
                #移除path
                seen_reads.discard(path)
            #是工具、且是都文档、并且不是最近的
            if item["role"] == "tool" and item["name"] == "read_file" and not recent:
                path = str(item["args"].get("path", ""))
                #添加到set集合里面
                if path in seen_reads:
                    continue
                seen_reads.add(path)
            #[tool:write_file] {"content": "Hello", "path": "/tmp/test.txt"}
            #content
            if item["role"] == "tool":
                limit = 900 if recent else 180
                lines.append(f"[tool:{item['name']}] {json.dumps(item['args'], sort_keys=True)}")
                lines.append(clip(item["content"], limit))
            else:
                #存的是user原话、retry的“model returned malformed tool JSON”重试说明、还有final的回答、次数用尽等
                limit = 900 if recent else 220
                lines.append(f"[{item['role']}] {clip(item['content'], limit)}")

        return clip("\n".join(lines), MAX_HISTORY)

    ########################################################
    #### 2) Prompt Shape And Cache Reuse (Continued) #######
    ########################################################
    #prompt分为四个部分：
    #1.前缀，一般一个Agent不会变动
    #2.记忆部分包含task、files（文档路径）、notes（干了哪些东西）三部分
    #3.历史记忆（经过压缩、去重、截断后拼成文本）
    #4.用户要求
    def prompt(self, user_message):
        return "\n\n".join([
            self.prefix,
            self.memory_text(),
            "对话记录：\n" + self.history_text(),
            "当前用户请求：\n" + user_message,
        ])

    ###############################################
    #### 5) Session Memory (Continued) ###########
    ###############################################
    #（ask相关）记录会话
    def record(self, item):
        #将会话添加到历史记录中
        self.session["history"].append(item)
        #保存会话到磁盘
        self.session_path = self.session_store.save(self.session)

    #（ask相关）将执行的工具files、notes记录到memory中
    def note_tool(self, name, args, result):
        memory = self.session["memory"]
        path = args.get("path")
        #读写等跟文件相关的放到files中
        if name in {"read_file", "write_file", "patch_file"} and path:
            self.remember(memory["files"], str(path), 8)
        #把工具结果压成一行note，最多220字符；换行换成空格
        note = f"{name}: {clip(str(result).replace(chr(10), ' '), 220)}"
        #最近的工具结果，放到notes中，最多 5 条。
        self.remember(memory["notes"], note, 5)

    #ask方法，主要分为tool、retry、final三种
    #注意点，task是我开启这个Agent对话的第一句话，后面的每句话都不会更改这个task，只会更改user_message
    def ask(self, user_message):
        # --plan-first：每条用户消息（一次 ask）开始时清零；仅当本轮（ask）内 tool_make_plan 成功可置 True
        # 跨轮 resume 不继承 satisfied；session 里 memory.plan 仍可被后续轮 prompt 读到
        self._ask_plan_satisfied = False
        memory = self.session["memory"]
        if not memory["task"]:
            #将用户输入的指令截断到300个字符
            memory["task"] = clip(user_message.strip(), 300)
        self.record({"role": "user", "content": user_message, "created_at": now()})

        #工具步数
        tool_steps = 0
        #尝试次数
        attempts = 0
        #最大尝试次数
        max_attempts = max(self.max_steps * 3, self.max_steps + 4)
        #如果工具步数小于最大步数且尝试次数小于最大尝试次数，则继续循环
        while tool_steps < self.max_steps and attempts < max_attempts:
            attempts += 1
            #调用模型客户端，生成响应
            raw = self.model_client.complete(self.prompt(user_message), self.max_new_tokens)
            #解析响应，分为标签和具体内容
            kind, payload = self.parse(raw)
            #如果kind为tool，则执行工具
            if kind == "tool":
                tool_steps += 1
                name = payload.get("name", "")
                args = payload.get("args", {})
                #得到工具调用后的结果
                result = self.run_tool(name, args)
                #先用一个变量记录基本的信息
                tool_record = {
                        "role": "tool",
                        #工具名字write_file等
                        "name": name,
                        "args": args,
                        "content": result,
                        "created_at": now(),
                    }
                #如果self._last_tool_meta不为空，则更新tool_record
                if self._last_tool_meta:
                    #将self._last_tool_meta的变更治理的附加信息更新到tool_record里面
                    tool_record.update(self._last_tool_meta)
                    #清空self._last_tool_meta，因为已经记录到tool_record里面了
                    self._last_tool_meta = {}
                #记录到历史中
                self.record(tool_record)
                #记录到memory中
                self.note_tool(name, args, result)
                continue

            if kind == "retry":
                #记录响应
                self.record({"role": "assistant", "content": payload, "created_at": now()})
                continue

            final = (payload or raw).strip()
            #记录响应
            self.record({"role": "assistant", "content": final, "created_at": now()})
            #记录到notes中
            self.remember(memory["notes"], clip(final, 220), 5)
            #返回最终答案
            return final

        if attempts >= max_attempts and tool_steps < self.max_steps:
            final = "已停止：模型多次返回无效 tool 或 final，未得到有效结果。"
        else:
            final = "已停止：达到步数上限仍未得到 final 回答。"
        self.record({"role": "assistant", "content": final, "created_at": now()})
        return final

    #############################################################
    #### 3) Structured Tools, Validation, And Permissions #######
    #############################################################
    def register_hook(self, event, handler):
        """Phase 2: 注册进程内 Hook 回调（pre_tool / post_tool）。"""
        self.hook_registry.register(event, handler)

    # 运行工具
    def run_tool(self, name, args):
        self._last_tool_meta = {}
        # 从build好的tools中找到对应的
        tool = self.tools.get(name)
        if tool is None:
            return f"错误：未知工具 '{name}'"
        try:
            # 校验工具是否可用
            self.validate_tool(name, args)
        except Exception as exc:
            example = self.tool_example(name)
            message = f"错误：{name} 参数无效：{exc}"
            if example:
                message += f"\n示例：{example}"
            return message
        # 校验是否连续使用工具，谨防死循环
        if self.repeated_tool_call(name, args):
            return self._invoke_tool_with_hooks(
                name,
                args,
                tool,
                lambda: (
                    f"错误：连续两次相同调用 {name}；请换用其他工具或返回 <final>"
                ),
            )
        # Phase 2: 校验通过后，经 Hook 包裹实际执行（含治理流程）
        return self._invoke_tool_with_hooks(
            name,
            args,
            tool,
            lambda: self._execute_tool_after_validation(name, args, tool),
        )

    def _invoke_tool_with_hooks(self, name, args, tool, execute):
        """Phase 2: 每次 run_tool 至多一对 pre_tool / post_tool。"""
        args = args or {}
        ctx = ToolHookContext(
            agent=self,
            name=name,
            args=args,
            tool=tool,
            risky=bool(tool.get("risky")),
        )
        self.hook_registry.emit_pre(ctx)
        result = execute()
        ctx.result = str(result)
        ctx.success = tool_result_success(result)
        self.hook_registry.emit_post(ctx)
        return result

    def _execute_tool_after_validation(self, name, args, tool):
        # Phase 3: --plan-first 门控（在 validate 之后、approve/治理之前；仅拦截 write/patch/shell）
        # 返回 error 字符串给主循环，不进入 _run_governed_file_tool / approve
        if self.plan_first and tool.get("risky") and not self._ask_plan_satisfied:
            return (
                "错误：已启用 --plan-first，请先在本轮 ask 内成功调用 make_plan，"
                f"再使用 risky 工具 '{name}'（write_file、patch_file、run_shell）"
            )
        # 这里调用_run_governed_file_tool，也就是治理主流程，不走传统的write_file两个工具了
        if name in {"write_file", "patch_file"}:
            return self._run_governed_file_tool(name, args)
        # 是否允许使用有风险的工具
        if tool["risky"] and not self.approve(name, args):
            return f"错误：{name} 审批被拒绝"
        try:
            # 在 build_tools() 里，每个工具都注册了 "run"，指向一个 Python 方法，"run": self.tool_read_file
            # tool["run"](args)等价于self.tool_read_file(args)
            # clip是指对得到的文本超过4k就进行截断
            return clip(tool["run"](args))
        except Exception as exc:
            return f"错误：工具 {name} 执行失败：{exc}"

    #校验是否已经使用该工具两次了，防止最近、连续（重点）使用三次该工具，如果最近三次一直都使用该工具，有很大概率卡死了。
    def repeated_tool_call(self, name, args):
        tool_events = [item for item in self.session["history"] if item["role"] == "tool"]
        if len(tool_events) < 2:
            return False
        #获取最近两次的，这个的语法是从倒数第二个一直获取到末尾，也就是两个，也就是说这是最近且连续的两次操作
        recent = tool_events[-2:]
        #如果两次都调用相同的工具，则返回false，报错，防死循环。
        return all(item["name"] == name and item["args"] == args for item in recent)

    #模型返回的工具格式示例
    def tool_example(self, name):
        examples = {
            "list_files": '<tool>{"name":"list_files","args":{"path":"."}}</tool>',
            "read_file": '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":80}}</tool>',
            "search": '<tool>{"name":"search","args":{"pattern":"binary_search","path":"."}}</tool>',
            "run_shell": '<tool>{"name":"run_shell","args":{"command":"uv run --with pytest python -m pytest -q","timeout":20}}</tool>',
            "write_file": '<tool name="write_file" path="binary_search.py"><content>def binary_search(nums, target):\n    return -1\n</content></tool>',
            "patch_file": '<tool name="patch_file" path="binary_search.py"><old_text>return -1</old_text><new_text>return mid</new_text></tool>',
            "delegate": '<tool>{"name":"delegate","args":{"task":"inspect README.md","max_steps":3}}</tool>',
            "make_plan": '<tool>{"name":"make_plan","args":{"goal":"add unit tests","context":"scanned src/"}}</tool>',
            "load_skill": '<tool>{"name":"load_skill","args":{"name":"code-review"}}</tool>',
        }
        return examples.get(name, "")

    #验证工具是否可用
    def validate_tool(self, name, args):
        args = args or {}
        #验证list的文件的路径是否能用，文件是否能打开
        if name == "list_files":
            path = self.path(args.get("path", "."))
            if not path.is_dir():
                raise ValueError("path 不是目录")
            return
        #验证要读的文件是否能打开，并且验证start和end是否合法
        if name == "read_file":
            path = self.path(args["path"])
            if not path.is_file():
                raise ValueError("path 不是文件")
            start = int(args.get("start", 1))
            end = int(args.get("end", 200))
            if start < 1 or end < start:
                raise ValueError("行范围无效（start/end）")
            return

        if name == "search":
            pattern = str(args.get("pattern", "")).strip()
            if not pattern:
                raise ValueError("参数 pattern 不能为空")
            self.path(args.get("path", "."))
            return

        if name == "run_shell":
            command = str(args.get("command", "")).strip()
            if not command:
                raise ValueError("参数 command 不能为空")
            timeout = int(args.get("timeout", 20))
            if timeout < 1 or timeout > 120:
                raise ValueError("参数 timeout 须在 1–120 之间")
            return

        if name == "write_file":
            path = self.path(args["path"])
            if path.exists() and path.is_dir():
                raise ValueError("path 是目录，不能写入")
            if "content" not in args:
                raise ValueError("缺少参数 content")
            return

        if name == "patch_file":
            path = self.path(args["path"])
            if not path.is_file():
                raise ValueError("path 不是文件")
            old_text = str(args.get("old_text", ""))
            if not old_text:
                raise ValueError("参数 old_text 不能为空")
            if "new_text" not in args:
                raise ValueError("缺少参数 new_text")
            text = path.read_text(encoding="utf-8")
            #记录old_text在整个text中有几处，如果不为1，则报错，因为不知道精确位置
            count = text.count(old_text)
            if count != 1:
                raise ValueError(f"参数 old_text 须恰好出现 1 次，实际出现 {count} 次")
            return

        if name == "delegate":
            if self.depth >= self.max_depth:
                raise ValueError("delegate 调用深度超限")
            task = str(args.get("task", "")).strip()
            if not task:
                raise ValueError("参数 task 不能为空")
            return

        # Phase 3: make_plan 只校验 goal；context 可选，由 planning prompt 消费
        if name == "make_plan":
            goal = str(args.get("goal", "")).strip()
            if not goal:
                raise ValueError("参数 goal 不能为空")
            return

        # Phase 4: load_skill 只校验 name
        if name == "load_skill":
            skill_name = str(args.get("name", "")).strip()
            if not skill_name:
                raise ValueError("参数 name 不能为空")
            return

    # 处理写文件和patch文件的治理主流程
    def _run_governed_file_tool(self, name, args):
        self._last_tool_meta = {}
        path = self.path(args["path"])
        rel_path = str(path.relative_to(self.root))
        #查看文件是否存在，在后续回溯的时候，如果存在，则恢复内容，如果不存在则直接删除
        existed = path.is_file()
        before = path.read_text(encoding="utf-8") if existed else ""
        #执行write_file或patch_file，得到proposed content。这里的before其实是整个text文本内容
        proposed = self._proposed_file_content(name, args, before)
        #计算diff，也就是计算这次tool的改动和上一次的改动之间的差异
        diff_text = build_unified_diff(rel_path, before, proposed)
        #查询git状态，如果有未提交的更改，则返回警告
        git_warning = self.workspace.git_dirty_warning()
        #受理并输出，用户进行审批，如果审批不通过，则返回错误
        if not self.approve(name, args, diff=diff_text, git_warning=git_warning):
            return f"错误：{name} 审批被拒绝"

        #只有write文件和patch文件需要保存checkpoint，其他工具不需要
        checkpoint = {
            #每一个治理的唯一id
            "id": "cp-" + uuid.uuid4().hex[:12],
            "session_id": self.session["id"],
            "tool_name": name,
            "path": rel_path,
            #文件是否存在，以便后续恢复还是删除
            "existed": existed,
            #恢复的文件内容，如果存在则返回，不存在则返回None
            "content": before if existed else None,
            #文件内容的sha256值，如果存在则返回，不存在则返回None
            "sha256_before": text_sha256(before) if existed else None,
            "created_at": now(),
        }
        try:
            #存到磁盘
            self.checkpoint_store.save(checkpoint)
        except Exception as exc:
            return f"错误：{name} 检查点保存失败：{exc}"

        #记录治理的附加信息,主要用于审计，后面通过record方法记录到session里面
        self._last_tool_meta = {
            #diff的摘要
            "diff_summary": diff_summary(diff_text),
            "checkpoint_id": checkpoint["id"],
            #是否回滚标识
            "rolled_back": False,
        }
        try:
            #原子写入文件，如果失败则回滚
            atomic_write_text(path, proposed)
        except Exception as exc:
            rollback = self._restore_checkpoint(checkpoint)
            self._last_tool_meta["rolled_back"] = True
            return f"错误：工具 {name} 执行失败：{exc}; {rollback}"

        if name == "write_file":
            return f"已写入 {rel_path}（{len(proposed)} 字符）"
        return f"已修补 {rel_path}"

    #如果是write_file，直接返回要写的内容，如果不是，那么就是patch_file，则替换旧内容为新内容，返回全部的text文本
    def _proposed_file_content(self, name, args, before):
        if name == "write_file":
            return str(args["content"])
        old_text = str(args.get("old_text", ""))
        return before.replace(old_text, str(args["new_text"]), 1)

    #回滚
    def _restore_checkpoint(self, checkpoint):
        path = self.root / checkpoint["path"]
        #如果文件不存在，则直接删除
        if not checkpoint["existed"]:
            if path.exists():
                path.unlink()
            return "已回滚：已删除新建文件"
        current_hash = file_sha256(path)
        before_hash = checkpoint["sha256_before"]
        #计算两者是否一样，不一样则跳过回滚，因为文件已被外部修改，无法恢复
        if current_hash is not None and before_hash is not None and current_hash != before_hash:
            return "回滚已跳过：文件已被外部修改"
        #恢复文件内容
        atomic_write_text(path, checkpoint["content"])
        return "已回滚：已恢复文件"

    #是否允许使用能修改你代码的工具（写、执行命令、替换)
    def approve(self, name, args, *, diff=None, git_warning=None):
        if self.read_only:
            return False
        if self.approval_policy == "auto":
            return True
        if self.approval_policy == "never":
            return False
        try:
            if diff is not None:
                rel_path = str(args.get("path", ""))
                print(f"--- 变更预览：{name} {rel_path} ---")
                print(diff)
                print("--- 变更预览结束 ---")
            if git_warning:
                print(git_warning)
            if diff is not None:
                answer = input("批准此次变更？[y/n] ")
            #因为diff是空，则有可能是其他risky工具，所以需要询问用户是否批准
            else:
                answer = input(f"批准 {name} {json.dumps(args, ensure_ascii=True)}？[y/n] ")
        except EOFError:
            return False
        return answer.strip().lower() in {"y", "yes"}

    @staticmethod
    #解析模型返回的结果
    def parse(raw):
        raw = str(raw)
        #tool首先存在，并且tool的位置比final靠前
        if "<tool>" in raw and ("<final>" not in raw or raw.find("<tool>") < raw.find("<final>")):
            body = MiniAgent.extract(raw, "tool")
            try:
                #将一个 JSON 格式的字符串解析（反序列化）成 Python 对象
                #payload的格式是字典，例子：{"name": "write_file", "args": {"path": "foo.py", "content": "..."}}
                payload = json.loads(body)
            except Exception:
                #如果解析失败，返回一个提示模型重试的消息(模型返回了错误格式的json)
                return "retry", MiniAgent.retry_notice("模型返回的 tool JSON 格式错误")
            if not isinstance(payload, dict):
                #需要是json格式
                return "retry", MiniAgent.retry_notice("tool 载荷必须是 JSON 对象")
            if not str(payload.get("name", "")).strip():
                return "retry", MiniAgent.retry_notice("tool 载荷缺少工具名 name")
            #获取args
            args = payload.get("args", {})
            if args is None:
                payload["args"] = {}
            elif not isinstance(args, dict):
                #不符合格式就重试
                return "retry", MiniAgent.retry_notice()
            return "tool", payload
        #tool首先存在，并且tool的位置比final靠前，且tool的格式是XML格式，类似这样：<tool name
        if "<tool" in raw and ("<final>" not in raw or raw.find("<tool") < raw.find("<final>")):
            payload = MiniAgent.parse_xml_tool(raw)
            if payload is not None:
                return "tool", payload
            return "retry", MiniAgent.retry_notice()
        if "<final>" in raw:
            final = MiniAgent.extract(raw, "final").strip()
            if final:
                return "final", final
            return "retry", MiniAgent.retry_notice("模型返回了空的 <final> 回答")
        raw = raw.strip()
        #兜底，前面都没进入的话，说明模型返回的纯文本，没有tool、final，因此返回该文本
        if raw:
            return "final", raw
        return "retry", MiniAgent.retry_notice("模型返回了空响应")

    #（属于parse）用于生成一个提示模型重试的标准化错误消息
    @staticmethod
    def retry_notice(problem=None):
        prefix = "运行时提示"
        if problem:
            prefix += f"：{problem}"
        else:
            prefix += "：模型返回了格式错误的 tool 输出"
        return (
            f"{prefix}。请使用有效的 <tool> 调用或非空的 <final> 回答。"
            '多行文件请优先使用 <tool name="write_file" path="file.py"><content>...</content></tool>。'
        )

    #（属于parse）解析XML格式的tool，返回想要使用的工具名称和参数（字典）
    @staticmethod
    def parse_xml_tool(raw):
        match = re.search(r"<tool(?P<attrs>[^>]*)>(?P<body>.*?)</tool>", raw, re.S)
        if not match:
            return None
        # attrs 解析结果示例：{"name": "write_file", "path": "foo.py"}
        attrs = MiniAgent.parse_attrs(match.group("attrs"))
        name = str(attrs.pop("name", "")).strip()
        if not name:
            return None
        # body 解析结果示例：<content>...</content>
        body = match.group("body")
        args = dict(attrs)
        # 遍历 body 中的 key，如果 key 在白名单中存在，则将key的值赋给 args[key]
        for key in ("content", "old_text", "new_text", "command", "task", "pattern", "path"):
            if f"<{key}>" in body:
                args[key] = MiniAgent.extract_raw(body, key)
        body_text = body.strip("\n")
        if name == "write_file" and "content" not in args and body_text:
            args["content"] = body_text
        if name == "delegate" and "task" not in args and body_text:
            args["task"] = body_text.strip()
        return {"name": name, "args": args}

    #（属于parse）parse_attrs 用正则找 key="value" 或 key='value'
    @staticmethod
    def parse_attrs(text):
        attrs = {}
        for match in re.finditer(r"""([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""", text):
            attrs[match.group(1)] = match.group(2) if match.group(2) is not None else match.group(3)
        return attrs

    #（属于parse）从文本中截取出指定 XML 风格标签（如 <tag>...</tag>）之间的内容，并去掉首尾空白字符。
    @staticmethod
    def extract(text, tag):
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        start = text.find(start_tag)
        if start == -1:
            return text
        start += len(start_tag)
        end = text.find(end_tag, start)
        if end == -1:
            return text[start:].strip()
        return text[start:end].strip()

    #（属于parse）从文本中截取出指定 XML 风格标签（如 <tag>...</tag>）之间的内容，保留空白，跟源文本一字不差
    @staticmethod
    def extract_raw(text, tag):
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        start = text.find(start_tag)
        if start == -1:
            return text
        start += len(start_tag)
        end = text.find(end_tag, start)
        if end == -1:
            return text[start:]
        return text[start:end]




    ###############################################
    #### 8) Skills (Phase 4) ######################
    ###############################################
    def _ensure_memory_shape(self):
        """旧 session 兼容：补齐 memory.loaded_skills 等 Phase 4 字段。"""
        memory = self.session.setdefault("memory", {})
        memory.setdefault("task", "")
        memory.setdefault("files", [])
        memory.setdefault("notes", [])
        memory.setdefault("plan", None)
        memory.setdefault("loaded_skills", {})

    def _preload_skills(self, names):
        """CLI --skills 预加载；失败项收集 warn，不阻止 Agent 启动。"""
        warnings = []
        for raw_name in names:
            name = str(raw_name).strip()
            if not name:
                continue
            result = self._load_skill_into_memory(name)
            if result.startswith("错误："):
                warnings.append(f"预加载 Skill '{name}' 失败：{result}")
        return warnings

    def _load_skill_into_memory(self, name):
        """阶段二：读 SKILL.md 正文写入 memory.loaded_skills；成功/失败均返回工具结果字符串。"""
        body, err = self.skill_catalog.read_body(name)
        if err:
            return err
        entry = self.skill_catalog.get(name)
        self.session["memory"]["loaded_skills"][name] = {
            "name": name,
            "description": entry.description,
            "body": body,
        }
        self.session_path = self.session_store.save(self.session)
        return format_load_skill_result(name, entry.description, body)

    def tool_load_skill(self, args):
        """safe 工具：加载 Skill 正文；重复加载同名 Skill 覆盖（幂等）。"""
        name = str(args.get("name", "")).strip()
        return self._load_skill_into_memory(name)

    #重置会话
    def reset(self):
        #清空历史记录
        self.session["history"] = []
        #清空记忆（含 Phase 3 memory.plan、Phase 4 loaded_skills）
        self.session["memory"] = {
            "task": "",
            "files": [],
            "notes": [],
            "plan": None,
            "loaded_skills": {},
        }
        #保存会话
        self.session_store.save(self.session)

    def path_is_within_root(self, resolved):
        probe = resolved
        while not probe.exists() and probe.parent != probe:
            probe = probe.parent
        for candidate in (probe, *probe.parents):
            try:
                if candidate.samefile(self.root):
                    return True
            except OSError:
                continue
        return False

    def path(self, raw_path):
        path = Path(raw_path)
        path = path if path.is_absolute() else self.root / path
        resolved = path.resolve()
        if not self.path_is_within_root(resolved):
            raise ValueError(f"路径超出工作区：{raw_path}")
        return resolved

    # 具体的工具实现
    def tool_list_files(self, args):
        path = self.path(args.get("path", "."))
        if not path.is_dir():
            raise ValueError("path 不是目录")
        entries = [
            item for item in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
            if item.name not in IGNORED_PATH_NAMES
        ]
        lines = []
        for entry in entries[:200]:
            kind = "[D]" if entry.is_dir() else "[F]"
            lines.append(f"{kind} {entry.relative_to(self.root)}")
        return "\n".join(lines) or "（空）"

    def tool_read_file(self, args):
        path = self.path(args["path"])
        if not path.is_file():
            raise ValueError("path 不是文件")
        start = int(args.get("start", 1))
        end = int(args.get("end", 200))
        if start < 1 or end < start:
            raise ValueError("行范围无效（start/end）")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        body = "\n".join(f"{number:>4}: {line}" for number, line in enumerate(lines[start - 1:end], start=start))
        return f"# {path.relative_to(self.root)}\n{body}"

    def tool_search(self, args):
        pattern = str(args.get("pattern", "")).strip()
        if not pattern:
            raise ValueError("参数 pattern 不能为空")
        path = self.path(args.get("path", "."))

        if shutil.which("rg"):
            result = subprocess.run(
                ["rg", "-n", "--smart-case", "--max-count", "200", pattern, str(path)],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() or result.stderr.strip() or "（无匹配）"

        matches = []
        files = [path] if path.is_file() else [
            item for item in path.rglob("*")
            if item.is_file() and not any(part in IGNORED_PATH_NAMES for part in item.relative_to(self.root).parts)
        ]
        for file_path in files:
            for number, line in enumerate(file_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                if pattern.lower() in line.lower():
                    matches.append(f"{file_path.relative_to(self.root)}:{number}:{line}")
                    if len(matches) >= 200:
                        return "\n".join(matches)
        return "\n".join(matches) or "（无匹配）"

    def tool_run_shell(self, args):
        command = str(args.get("command", "")).strip()
        if not command:
            raise ValueError("参数 command 不能为空")
        timeout = int(args.get("timeout", 20))
        if timeout < 1 or timeout > 120:
            raise ValueError("参数 timeout 须在 1–120 之间")
        result = subprocess.run(
            command,
            cwd=self.root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return "\n".join(
            [
                f"exit_code: {result.returncode}",
                "stdout:",
                result.stdout.strip() or "（空）",
                "stderr:",
                result.stderr.strip() or "（空）",
            ]
        )

    def tool_write_file(self, args):
        path = self.path(args["path"])
        content = str(args["content"])
        atomic_write_text(path, content)
        return f"已写入 {path.relative_to(self.root)}（{len(content)} 字符）"

    def tool_patch_file(self, args):
        path = self.path(args["path"])
        if not path.is_file():
            raise ValueError("path 不是文件")
        old_text = str(args.get("old_text", ""))
        if not old_text:
            raise ValueError("参数 old_text 不能为空")
        if "new_text" not in args:
            raise ValueError("缺少参数 new_text")
        text = path.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count != 1:
            raise ValueError(f"参数 old_text 须恰好出现 1 次，实际出现 {count} 次")
        atomic_write_text(path, text.replace(old_text, str(args["new_text"]), 1))
        return f"已修补 {path.relative_to(self.root)}"

    ###################################################
    #### 7) Task Planning (Phase 3) ###################
    ###################################################
    # 与 delegate 对比：不创建子 Agent、不占用 ask 的 tool_steps；一次 complete + JSON 校验
    def tool_make_plan(self, args):
        """单次 planning 模型调用；成功则写入 session memory.plan 并满足 --plan-first 门控。"""
        goal = str(args.get("goal", "")).strip()
        context = str(args.get("context", "")).strip()
        planning_prompt = build_planning_prompt(goal, context, self.workspace.text())
        # 专用 complete，只返回相应的json结果，不像其他的工具都是直接执行py，或者是问LLM要哪些工具，但返回的都是<tool>。。
        raw = self.model_client.complete(planning_prompt, self.max_new_tokens)
        try:
            plan = parse_plan_response(raw)
        except ValueError as exc:
            # 解析失败不写 memory.plan，主循环可将 error 当 tool 结果继续 retry
            return f"错误：make_plan 失败：{exc}"
        self.session["memory"]["plan"] = plan
        self._ask_plan_satisfied = True  # 仅当轮 ask 有效；下一条用户消息在 ask() 开头会清零
        self.session_path = self.session_store.save(self.session)
        return format_plan_tool_result(plan)

    ###################################################
    #### 6) Delegation And Bounded Subagents ##########
    ###################################################
    #创建并调用子Agent完成一些读的操作
    def tool_delegate(self, args):
        if self.depth >= self.max_depth:
            raise ValueError("delegate 调用深度超限")
        task = str(args.get("task", "")).strip()
        if not task:
            raise ValueError("参数 task 不能为空")
        child = MiniAgent(
            model_client=self.model_client,
            workspace=self.workspace,
            session_store=self.session_store,
            approval_policy="never",
            max_steps=int(args.get("max_steps", 3)),
            max_new_tokens=self.max_new_tokens,
            depth=self.depth + 1,
            max_depth=self.max_depth,
            read_only=True,
            enable_trace_hook=True,
            hook_config=self.hook_config,
        )
        child.session["memory"]["task"] = task
        #notes的第一个会截取历史信息放进去
        child.session["memory"]["notes"] = [clip(self.history_text(), 300)]
        return "delegate 结果：\n" + child.ask(task)

