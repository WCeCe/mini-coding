import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from mini_coding_agent.constants import IGNORED_PATH_NAMES, MAX_HISTORY
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
        # Phase 2/2.1: 工具边界 Hook 注册表；YAML + 内置 Hook 栈
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
            "memory": {"task": "", "files": [], "notes": []},
        }
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
                "description": "List files in the workspace.",
                "run": self.tool_list_files,
            },
            #有大小限制
            "read_file": {
                "schema": {"path": "str", "start": "int=1", "end": "int=200"},
                "risky": False,
                "description": "Read a UTF-8 file by line range.",
                "run": self.tool_read_file,
            },
            #pattern要在代码/文件里查找的文字
            "search": {
                "schema": {"pattern": "str", "path": "str='.'"},
                "risky": False,
                "description": "Search the workspace with rg or a simple fallback.",
                "run": self.tool_search,
            },
            #command要执行的命令
            "run_shell": {
                "schema": {"command": "str", "timeout": "int=20"},
                "risky": True,
                "description": "Run a shell command in the repo root.",
                "run": self.tool_run_shell,
            },
            #content要写入的文本内容
            "write_file": {
                "schema": {"path": "str", "content": "str"},
                "risky": True,
                "description": "Write a text file.",
                "run": self.tool_write_file,
            },
            #精确文本替换，old_text源文本中要被替换的那一段，new_text要替换的
            "patch_file": {
                "schema": {"path": "str", "old_text": "str", "new_text": "str"},
                "risky": True,
                "description": "Replace one exact text block in a file.",
                "run": self.tool_patch_file,
            },
        }
        #max_depth为1，只允许调用一层子Agent，子Agent不能继续往下调用；且子Agent只读
        if self.depth < self.max_depth:
            tools["delegate"] = {
                "schema": {"task": "str", "max_steps": "int=3"},
                "risky": False,
                "description": "Ask a bounded read-only child agent to investigate.",
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
            risk = "approval required" if tool["risky"] else "safe"
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
                "<final>Done.</final>",
            ]
        )
        #3.规则
        rules = "\n".join([
            "- Use tools instead of guessing about the workspace.",
            "- Return exactly one <tool>...</tool> or one <final>...</final>.",
            "- Tool calls must look like:",
            '  <tool>{"name":"tool_name","args":{...}}</tool>',
            "- For write_file and patch_file with multi-line text, prefer XML style:",
            '  <tool name="write_file" path="file.py"><content>...</content></tool>',
            "- Final answers must look like:",
            "  <final>your answer</final>",
            "- Never invent tool results.",
            "- Keep answers concise and concrete.",
            "- If the user asks you to create or update a specific file and the path is clear, use write_file or patch_file instead of repeatedly listing files.",
            "- Before writing tests for existing code, read the implementation first.",
            "- When writing tests, match the current implementation unless the user explicitly asked you to change the code.",
            "- New files should be complete and runnable, including obvious imports.",
            "- Do not repeat the same tool call with the same arguments if it did not help. Choose a different tool or return a final answer.",
            "- Required tool arguments must not be empty. Do not call read_file, write_file, patch_file, run_shell, or delegate with args={}.",
        ])
        #构建prompt的prefix部分，prefix又分为五个部分：
        #1.You are Mini-Coding-Agent...
        #2. 规则：Rules: + rules
        #3. 工具列表：Tools: + tool_lines
        #4. 案例：Valid response examples: + examples
        #5. 仓库快照：workspace.text()（仓库快照）
        return "\n\n".join([
            "You are Mini-Coding-Agent, a small local coding agent running through Ollama.",
            "Rules:\n" + rules,
            "Tools:\n" + tool_text,
            "Valid response examples:\n" + examples,
            self.workspace.text(),
        ])

    #构建memory
    def memory_text(self):
        memory = self.session["memory"]
        notes = "\n".join(f"- {note}" for note in memory["notes"]) or "- none"
        return "\n".join([
            "Memory:",
            f"- task: {memory['task'] or '-'}",
            f"- files: {', '.join(memory['files']) or '-'}",
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
            return "- empty"
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
            "Transcript:\n" + self.history_text(),
            "Current user request:\n" + user_message,
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
            final = "Stopped after too many malformed model responses without a valid tool call or final answer."
        else:
            final = "Stopped after reaching the step limit without a final answer."
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
            return f"error: unknown tool '{name}'"
        try:
            # 校验工具是否可用
            self.validate_tool(name, args)
        except Exception as exc:
            example = self.tool_example(name)
            message = f"error: invalid arguments for {name}: {exc}"
            if example:
                message += f"\nexample: {example}"
            return message
        # 校验是否连续使用工具，谨防死循环
        if self.repeated_tool_call(name, args):
            return self._invoke_tool_with_hooks(
                name,
                args,
                tool,
                lambda: (
                    f"error: repeated identical tool call for {name}; "
                    "choose a different tool or return a final answer"
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
            return f"error: tool {name} failed: {exc}"

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
        }
        return examples.get(name, "")

    #验证工具是否可用
    def validate_tool(self, name, args):
        args = args or {}
        #验证list的文件的路径是否能用，文件是否能打开
        if name == "list_files":
            path = self.path(args.get("path", "."))
            if not path.is_dir():
                raise ValueError("path is not a directory")
            return
        #验证要读的文件是否能打开，并且验证start和end是否合法
        if name == "read_file":
            path = self.path(args["path"])
            if not path.is_file():
                raise ValueError("path is not a file")
            start = int(args.get("start", 1))
            end = int(args.get("end", 200))
            if start < 1 or end < start:
                raise ValueError("invalid line range")
            return

        if name == "search":
            pattern = str(args.get("pattern", "")).strip()
            if not pattern:
                raise ValueError("pattern must not be empty")
            self.path(args.get("path", "."))
            return

        if name == "run_shell":
            command = str(args.get("command", "")).strip()
            if not command:
                raise ValueError("command must not be empty")
            timeout = int(args.get("timeout", 20))
            if timeout < 1 or timeout > 120:
                raise ValueError("timeout must be in [1, 120]")
            return

        if name == "write_file":
            path = self.path(args["path"])
            if path.exists() and path.is_dir():
                raise ValueError("path is a directory")
            if "content" not in args:
                raise ValueError("missing content")
            return

        if name == "patch_file":
            path = self.path(args["path"])
            if not path.is_file():
                raise ValueError("path is not a file")
            old_text = str(args.get("old_text", ""))
            if not old_text:
                raise ValueError("old_text must not be empty")
            if "new_text" not in args:
                raise ValueError("missing new_text")
            text = path.read_text(encoding="utf-8")
            #记录old_text在整个text中有几处，如果不为1，则报错，因为不知道精确位置
            count = text.count(old_text)
            if count != 1:
                raise ValueError(f"old_text must occur exactly once, found {count}")
            return

        if name == "delegate":
            if self.depth >= self.max_depth:
                raise ValueError("delegate depth exceeded")
            task = str(args.get("task", "")).strip()
            if not task:
                raise ValueError("task must not be empty")
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
            return f"wrote {rel_path} ({len(proposed)} chars)"
        return f"patched {rel_path}"

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
                print(f"--- change preview: {name} {rel_path} ---")
                print(diff)
                print("--- end diff ---")
            if git_warning:
                print(git_warning)
            if diff is not None:
                answer = input("approve this change? [y/n] ")
            #因为diff是空，则有可能是其他risky工具，所以需要询问用户是否批准
            else:
                answer = input(f"approve {name} {json.dumps(args, ensure_ascii=True)}? [y/n] ")
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
                return "retry", MiniAgent.retry_notice("model returned malformed tool JSON")
            if not isinstance(payload, dict):
                #需要是json格式
                return "retry", MiniAgent.retry_notice("tool payload must be a JSON object")
            if not str(payload.get("name", "")).strip():
                return "retry", MiniAgent.retry_notice("tool payload is missing a tool name")
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
            return "retry", MiniAgent.retry_notice("model returned an empty <final> answer")
        raw = raw.strip()
        #兜底，前面都没进入的话，说明模型返回的纯文本，没有tool、final，因此返回该文本
        if raw:
            return "final", raw
        return "retry", MiniAgent.retry_notice("model returned an empty response")

    #（属于parse）用于生成一个提示模型重试的标准化错误消息
    @staticmethod
    def retry_notice(problem=None):
        prefix = "Runtime notice"
        if problem:
            prefix += f": {problem}"
        else:
            prefix += ": model returned malformed tool output"
        return (
            f"{prefix}. Reply with a valid <tool> call or a non-empty <final> answer. "
            'For multi-line files, prefer <tool name="write_file" path="file.py"><content>...</content></tool>.'
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




    #重置会话
    def reset(self):
        #清空历史记录
        self.session["history"] = []
        #清空记忆
        self.session["memory"] = {"task": "", "files": [], "notes": []}
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
            raise ValueError(f"path escapes workspace: {raw_path}")
        return resolved

    # 具体的工具实现
    def tool_list_files(self, args):
        path = self.path(args.get("path", "."))
        if not path.is_dir():
            raise ValueError("path is not a directory")
        entries = [
            item for item in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
            if item.name not in IGNORED_PATH_NAMES
        ]
        lines = []
        for entry in entries[:200]:
            kind = "[D]" if entry.is_dir() else "[F]"
            lines.append(f"{kind} {entry.relative_to(self.root)}")
        return "\n".join(lines) or "(empty)"

    def tool_read_file(self, args):
        path = self.path(args["path"])
        if not path.is_file():
            raise ValueError("path is not a file")
        start = int(args.get("start", 1))
        end = int(args.get("end", 200))
        if start < 1 or end < start:
            raise ValueError("invalid line range")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        body = "\n".join(f"{number:>4}: {line}" for number, line in enumerate(lines[start - 1:end], start=start))
        return f"# {path.relative_to(self.root)}\n{body}"

    def tool_search(self, args):
        pattern = str(args.get("pattern", "")).strip()
        if not pattern:
            raise ValueError("pattern must not be empty")
        path = self.path(args.get("path", "."))

        if shutil.which("rg"):
            result = subprocess.run(
                ["rg", "-n", "--smart-case", "--max-count", "200", pattern, str(path)],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() or result.stderr.strip() or "(no matches)"

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
        return "\n".join(matches) or "(no matches)"

    def tool_run_shell(self, args):
        command = str(args.get("command", "")).strip()
        if not command:
            raise ValueError("command must not be empty")
        timeout = int(args.get("timeout", 20))
        if timeout < 1 or timeout > 120:
            raise ValueError("timeout must be in [1, 120]")
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
                result.stdout.strip() or "(empty)",
                "stderr:",
                result.stderr.strip() or "(empty)",
            ]
        )

    def tool_write_file(self, args):
        path = self.path(args["path"])
        content = str(args["content"])
        atomic_write_text(path, content)
        return f"wrote {path.relative_to(self.root)} ({len(content)} chars)"

    def tool_patch_file(self, args):
        path = self.path(args["path"])
        if not path.is_file():
            raise ValueError("path is not a file")
        old_text = str(args.get("old_text", ""))
        if not old_text:
            raise ValueError("old_text must not be empty")
        if "new_text" not in args:
            raise ValueError("missing new_text")
        text = path.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count != 1:
            raise ValueError(f"old_text must occur exactly once, found {count}")
        atomic_write_text(path, text.replace(old_text, str(args["new_text"]), 1))
        return f"patched {path.relative_to(self.root)}"

    ###################################################
    #### 6) Delegation And Bounded Subagents ##########
    ###################################################
    #创建并调用子Agent完成一些读的操作
    def tool_delegate(self, args):
        if self.depth >= self.max_depth:
            raise ValueError("delegate depth exceeded")
        task = str(args.get("task", "")).strip()
        if not task:
            raise ValueError("task must not be empty")
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
        return "delegate_result:\n" + child.ask(task)

