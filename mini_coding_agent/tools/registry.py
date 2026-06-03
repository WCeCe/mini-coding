"""build_tools 注册表。"""

from mini_coding_agent.tools import implementations as impl


# 搭建tools字典
def build_tools(agent):
    tools = {
        "list_files": {
            "schema": {"path": "str='.'"},
            "risky": False,
            "description": "列出工作区中的文件与目录。",
            "run": lambda args: impl.tool_list_files(agent, args),
        },
        # 有大小限制
        "read_file": {
            "schema": {"path": "str", "start": "int=1", "end": "int=200"},
            "risky": False,
            "description": "按行范围读取 UTF-8 文本文件。",
            "run": lambda args: impl.tool_read_file(agent, args),
        },
        # pattern要在代码/文件里查找的文字
        "search": {
            "schema": {"pattern": "str", "path": "str='.'"},
            "risky": False,
            "description": "在工作区中搜索（优先 rg，否则简单回退）。",
            "run": lambda args: impl.tool_search(agent, args),
        },
        # command要执行的命令
        "run_shell": {
            "schema": {"command": "str", "timeout": "int=20"},
            "risky": True,
            "description": "在仓库根目录执行 shell 命令。",
            "run": lambda args: impl.tool_run_shell(agent, args),
        },
        # content要写入的文本内容；执行经 governance.run_governed_file_tool，无直写 run
        "write_file": {
            "schema": {"path": "str", "content": "str"},
            "risky": True,
            "description": "写入文本文件。",
        },
        # 精确文本替换，old_text源文本中要被替换的那一段，new_text要替换的；执行经治理链
        "patch_file": {
            "schema": {"path": "str", "old_text": "str", "new_text": "str"},
            "risky": True,
            "description": "在文件中精确替换一段文本。",
        },
        # Phase 3: 单次 complete 产出任务级计划（无内部 tool 循环）；全 depth 注册
        # 与 delegate 区别：delegate=子 Agent 多步只读调查，仅 depth<max_depth；make_plan=本层一次规划
        "make_plan": {
            "schema": {"goal": "str", "context": "str=''"},
            "risky": False,
            "description": "生成结构化任务级计划（单次 make_plan 调用，无内部 tool 循环）。",
            "run": lambda args: impl.tool_make_plan(agent, args),
        },
        # Phase 4: 按需加载 Skill 正文到 session memory（safe；observe-only）
        "load_skill": {
            "schema": {"name": "str"},
            "risky": False,
            "description": "加载仓库 Skill 正文到 session memory（启动时 prefix 仅含 metadata 清单）。",
            "run": lambda args: impl.tool_load_skill(agent, args),
        },
    }
    # max_depth为1，只允许调用一层子Agent，子Agent不能继续往下调用；且子Agent只读
    if agent.depth < agent.max_depth:
        tools["delegate"] = {
            "schema": {"task": "str", "max_steps": "int=3"},
            "risky": False,
            "description": "调用有界只读子 Agent 进行调查。",
            "run": lambda args: impl.tool_delegate(agent, args),
        }
    return tools
