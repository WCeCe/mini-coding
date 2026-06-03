"""各 tool_* 实现（write/patch 经 runtime 走 governance，不在此直写）。"""

import shutil
import subprocess

from mini_coding_agent.constants import IGNORED_PATH_NAMES
from mini_coding_agent.planning import (
    build_planning_prompt,
    format_plan_tool_result,
    parse_plan_response,
)
from mini_coding_agent.util import clip
from mini_coding_agent.wait_display import MESSAGE_PLAN, complete_with_wait_display


def tool_list_files(agent, args):
    path = agent.path(args.get("path", "."))
    if not path.is_dir():
        raise ValueError("path 不是目录")
    entries = [
        item for item in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        if item.name not in IGNORED_PATH_NAMES
    ]
    lines = []
    for entry in entries[:200]:
        kind = "[D]" if entry.is_dir() else "[F]"
        lines.append(f"{kind} {entry.relative_to(agent.root)}")
    return "\n".join(lines) or "（空）"


def tool_read_file(agent, args):
    path = agent.path(args["path"])
    if not path.is_file():
        raise ValueError("path 不是文件")
    start = int(args.get("start", 1))
    end = int(args.get("end", 200))
    if start < 1 or end < start:
        raise ValueError("行范围无效（start/end）")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    body = "\n".join(f"{number:>4}: {line}" for number, line in enumerate(lines[start - 1:end], start=start))
    return f"# {path.relative_to(agent.root)}\n{body}"


def tool_search(agent, args):
    pattern = str(args.get("pattern", "")).strip()
    if not pattern:
        raise ValueError("参数 pattern 不能为空")
    path = agent.path(args.get("path", "."))

    if shutil.which("rg"):
        result = subprocess.run(
            ["rg", "-n", "--smart-case", "--max-count", "200", pattern, str(path)],
            cwd=agent.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip() or result.stderr.strip() or "（无匹配）"

    matches = []
    files = [path] if path.is_file() else [
        item for item in path.rglob("*")
        if item.is_file() and not any(part in IGNORED_PATH_NAMES for part in item.relative_to(agent.root).parts)
    ]
    for file_path in files:
        for number, line in enumerate(file_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if pattern.lower() in line.lower():
                matches.append(f"{file_path.relative_to(agent.root)}:{number}:{line}")
                if len(matches) >= 200:
                    return "\n".join(matches)
    return "\n".join(matches) or "（无匹配）"


def tool_run_shell(agent, args):
    command = str(args.get("command", "")).strip()
    if not command:
        raise ValueError("参数 command 不能为空")
    timeout = int(args.get("timeout", 20))
    if timeout < 1 or timeout > 120:
        raise ValueError("参数 timeout 须在 1–120 之间")
    result = subprocess.run(
        command,
        cwd=agent.root,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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


# 与 delegate 对比：不创建子 Agent、不占用 ask 的 tool_steps；一次 complete + JSON 校验
def tool_make_plan(agent, args):
    """单次 planning 模型调用；成功则写入 session memory.plan 并满足 --plan-first 门控。"""
    goal = str(args.get("goal", "")).strip()
    context = str(args.get("context", "")).strip()
    planning_prompt = build_planning_prompt(goal, context, agent.workspace.text())
    # 专用 complete，只返回相应的json结果，不像其他的工具都是直接执行py，或者是问LLM要哪些工具，但返回的都是<tool>。。
    raw = complete_with_wait_display(
        agent.model_client,
        planning_prompt,
        agent.max_new_tokens,
        message=MESSAGE_PLAN,
    )
    try:
        plan = parse_plan_response(raw)
    except ValueError as exc:
        # 解析失败不写 memory.plan，主循环可将 error 当 tool 结果继续 retry
        return f"错误：make_plan 失败：{exc}"
    agent.session["memory"]["plan"] = plan
    agent._ask_plan_satisfied = True  # 仅当轮 ask 有效；下一条用户消息在 ask() 开头会清零
    agent.session_path = agent.session_store.save(agent.session)
    return format_plan_tool_result(plan)


# 创建并调用子Agent完成一些读的操作
def tool_delegate(agent, args):
    if agent.depth >= agent.max_depth:
        raise ValueError("delegate 调用深度超限")
    task = str(args.get("task", "")).strip()
    if not task:
        raise ValueError("参数 task 不能为空")
    from mini_coding_agent.agent import MiniAgent

    child = MiniAgent(
        model_client=agent.model_client,
        workspace=agent.workspace,
        session_store=agent.session_store,
        approval_policy="never",
        max_steps=int(args.get("max_steps", 3)),
        max_new_tokens=agent.max_new_tokens,
        depth=agent.depth + 1,
        max_depth=agent.max_depth,
        read_only=True,
        enable_trace_hook=True,
        hook_config=agent.hook_config,
    )
    child.session["memory"]["task"] = task
    # notes的第一个会截取历史信息放进去
    child.session["memory"]["notes"] = [clip(agent.history_text(), 300)]
    return "delegate 结果：\n" + child.ask(task)


def tool_load_skill(agent, args):
    """safe 工具：加载 Skill 正文；重复加载同名 Skill 覆盖（幂等）。"""
    name = str(args.get("name", "")).strip()
    return agent._load_skill_into_memory(name)
