"""工具参数校验、示例与重复调用检测。"""


# 模型返回的工具格式示例
def tool_example(name):
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


# 校验是否已经使用该工具两次了，防止最近、连续（重点）使用三次该工具，如果最近三次一直都使用该工具，有很大概率卡死了。
def repeated_tool_call(history, name, args):
    tool_events = [item for item in history if item["role"] == "tool"]
    if len(tool_events) < 2:
        return False
    # 获取最近两次的，这个的语法是从倒数第二个一直获取到末尾，也就是两个，也就是说这是最近且连续的两次操作
    recent = tool_events[-2:]
    # 如果两次都调用相同的工具，则返回false，报错，防死循环。
    return all(item["name"] == name and item["args"] == args for item in recent)


# 验证工具是否可用
def validate_tool(agent, name, args):
    args = args or {}
    # 验证list的文件的路径是否能用，文件是否能打开
    if name == "list_files":
        path = agent.path(args.get("path", "."))
        if not path.is_dir():
            raise ValueError("path 不是目录")
        return
    # 验证要读的文件是否能打开，并且验证start和end是否合法
    if name == "read_file":
        path = agent.path(args["path"])
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
        agent.path(args.get("path", "."))
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
        path = agent.path(args["path"])
        if path.exists() and path.is_dir():
            raise ValueError("path 是目录，不能写入")
        if "content" not in args:
            raise ValueError("缺少参数 content")
        return

    if name == "patch_file":
        path = agent.path(args["path"])
        if not path.is_file():
            raise ValueError("path 不是文件")
        old_text = str(args.get("old_text", ""))
        if not old_text:
            raise ValueError("参数 old_text 不能为空")
        if "new_text" not in args:
            raise ValueError("缺少参数 new_text")
        text = path.read_text(encoding="utf-8")
        # 记录old_text在整个text中有几处，如果不为1，则报错，因为不知道精确位置
        count = text.count(old_text)
        if count != 1:
            raise ValueError(f"参数 old_text 须恰好出现 1 次，实际出现 {count} 次")
        return

    if name == "delegate":
        if agent.depth >= agent.max_depth:
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
