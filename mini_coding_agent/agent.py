import uuid
from datetime import datetime
from pathlib import Path

from mini_coding_agent.governance import approve as approve_change
from mini_coding_agent.governance import restore_checkpoint
from mini_coding_agent.hooks.hook_config import default_hook_config, emit_config_warnings, load_hook_config
from mini_coding_agent.hooks import HookRegistry, register_builtin_hooks
from mini_coding_agent.protocol import parse
from mini_coding_agent.prompt import build_prefix as build_agent_prefix
from mini_coding_agent.prompt import build_prompt, history_text as format_history_text
from mini_coding_agent.prompt import memory_text as format_memory_text
from mini_coding_agent.session import CheckpointStore
from mini_coding_agent.skills import (
    SkillCatalog,
    emit_skill_warnings,
    format_load_skill_result,
)
from mini_coding_agent.tools import build_tools as build_agent_tools
from mini_coding_agent.tools import run_tool as execute_tool
from mini_coding_agent.tools.sandbox import path_is_within_root as check_path_in_root
from mini_coding_agent.tools.sandbox import resolve_path
from mini_coding_agent.util import clip, now
from mini_coding_agent.wait_display import MESSAGE_MODEL, complete_with_wait_display


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
        self.tools = build_agent_tools(self)
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

    ############################################
    #### 2) Prompt Shape And Cache Reuse #######
    ############################################
    # Prompt 形状（build_prefix / memory_text / history_text / prompt）见 mini_coding_agent.prompt

    def build_prefix(self):
        return build_agent_prefix(self.tools, self.skill_catalog, self.workspace)

    def memory_text(self):
        return format_memory_text(self.session["memory"])

    def history_text(self):
        return format_history_text(self.session["history"])

    def prompt(self, user_message):
        return build_prompt(
            self.prefix,
            self.session["memory"],
            self.session["history"],
            user_message,
        )

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
            raw = complete_with_wait_display(
                self.model_client,
                self.prompt(user_message),
                self.max_new_tokens,
                message=MESSAGE_MODEL,
            )
            #解析响应，分为标签和具体内容
            kind, payload = parse(raw)
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
    # 工具注册、validate、run 管道见 mini_coding_agent.tools

    def register_hook(self, event, handler):
        """Phase 2: 注册进程内 Hook 回调（pre_tool / post_tool）。"""
        self.hook_registry.register(event, handler)

    def run_tool(self, name, args):
        return execute_tool(self, name, args)

    def approve(self, name, args, *, diff=None, git_warning=None):
        """Phase 1 审批；实现见 mini_coding_agent.governance.approve。"""
        return approve_change(
            name,
            args,
            read_only=self.read_only,
            approval_policy=self.approval_policy,
            diff=diff,
            git_warning=git_warning,
        )

    def _restore_checkpoint(self, checkpoint):
        """回滚；实现见 mini_coding_agent.governance.restore_checkpoint。"""
        return restore_checkpoint(self.root, checkpoint)

    def path_is_within_root(self, resolved):
        return check_path_in_root(self.root, resolved)

    def path(self, raw_path):
        return resolve_path(self.root, raw_path)

    # 模型输出协议解析（parse / XML / retry）见 mini_coding_agent.protocol
    # Phase 1 变更治理（diff / checkpoint / approve / 回滚）见 mini_coding_agent.governance

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
