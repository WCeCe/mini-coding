import argparse
import shutil
import sys
from pathlib import Path

from mini_coding_agent.agent import MiniAgent
from mini_coding_agent.constants import HELP_DETAILS, WELCOME_ART
from mini_coding_agent.hooks.hook_config import apply_cli_overrides, emit_config_warnings, load_hook_config
from mini_coding_agent.models import OllamaModelClient
from mini_coding_agent.session import SessionStore
from mini_coding_agent.util import middle
from mini_coding_agent.workspace import WorkspaceContext


# 在控制台打印界面
def build_welcome(agent, model, host):
    width = max(68, min(shutil.get_terminal_size((80, 20)).columns, 84))
    inner = width - 4
    gap = 3
    left_width = (inner - gap) // 2
    right_width = inner - gap - left_width

    def row(text):
        body = middle(text, width - 4)
        return f"| {body.ljust(width - 4)} |"

    def divider(char="-"):
        return "+" + char * (width - 2) + "+"

    def center(text):
        body = middle(text, inner)
        return f"| {body.center(inner)} |"

    def cell(label, value, size):
        body = middle(f"{label:<9} {value}", size)
        return body.ljust(size)

    def pair(left_label, left_value, right_label, right_value):
        left = cell(left_label, left_value, left_width)
        right = cell(right_label, right_value, right_width)
        return f"| {left}{' ' * gap}{right} |"

    line = divider("=")
    rows = [center(text) for text in WELCOME_ART]
    rows.extend(
        [
            center("MINI CODING AGENT"),
            divider("-"),
            row(""),
            row("WORKSPACE  " + middle(agent.workspace.cwd, inner - 11)),
            pair("MODEL", model, "BRANCH", agent.workspace.branch),
            pair("APPROVAL", agent.approval_policy, "SESSION", agent.session["id"]),
            row(""),
        ]
    )
    return "\n".join([line, *rows, line])


# 构建agent
def build_agent(args):
    # 构建工作空间上下文
    workspace = WorkspaceContext.build(args.cwd)
    # 构建会话存储
    store = SessionStore(Path(workspace.repo_root) / ".mini-coding-agent" / "sessions")
    # 构建模型客户端
    model = OllamaModelClient(
        model=args.model,
        host=args.host,
        temperature=args.temperature,
        top_p=args.top_p,
        timeout=args.ollama_timeout,
    )

    # Phase 2.1: 加载 hooks.yaml，CLI 旗标可覆盖
    hooks_path = (
        Path(args.hooks_config)
        if args.hooks_config
        else Path(workspace.repo_root) / ".mini-coding-agent" / "hooks.yaml"
    )
    hook_config, config_warnings = load_hook_config(hooks_path)
    emit_config_warnings(config_warnings)
    hook_config = apply_cli_overrides(hook_config, args)

    # 获取session_id，构建一个Agent对象
    # 解析命令行，python mini_coding_agent.py --resume latest
    session_id = args.resume
    agent_kwargs = dict(
        approval_policy=args.approval,
        max_steps=args.max_steps,
        max_new_tokens=args.max_new_tokens,
        hook_config=hook_config,
        # Phase 3: --plan-first → 每条 ask 须先成功 make_plan 再允许 risky tool
        plan_first=args.plan_first,
    )
    if session_id == "latest":
        session_id = store.latest()
    # 如果session_id不为空，则会话存储中加载session
    if session_id:
        return MiniAgent.from_session(
            model_client=model,
            workspace=workspace,
            session_store=store,
            session_id=session_id,
            **agent_kwargs,
        )
    # 如果没有旧会话，则初始化新的Agent对象
    return MiniAgent(
        model_client=model,
        workspace=workspace,
        session_store=store,
        **agent_kwargs,
    )


# 构建args
def build_arg_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="基于 Ollama 的本地小型编程 Agent。",
    )
    parser.add_argument("prompt", nargs="*", help="可选：一次性任务提示（不跟则进入 REPL）。")
    parser.add_argument("--cwd", default=".", help="工作区目录。")
    parser.add_argument("--model", default="qwen3.5:4b", help="Ollama 模型名称。")
    parser.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama 服务地址。")
    parser.add_argument("--ollama-timeout", type=int, default=300, help="Ollama 请求超时（秒）。")
    parser.add_argument("--resume", default=None, help="恢复的 session id，或 latest。")
    parser.add_argument(
        "--approval",
        choices=("ask", "auto", "never"),
        default="ask",
        help="risky 工具审批策略；auto 表示自动批准写文件与 run_shell。",
    )
    parser.add_argument("--max-steps", type=int, default=6, help="每条请求的最大 tool/模型迭代次数。")
    parser.add_argument("--max-new-tokens", type=int, default=512, help="每步模型最大输出 token 数。")
    parser.add_argument("--temperature", type=float, default=0.2, help="发给 Ollama 的采样 temperature。")
    parser.add_argument("--top-p", type=float, default=0.9, help="发给 Ollama 的 top-p。")
    parser.add_argument(
        "--hooks-config",
        default=None,
        help="hooks.yaml 路径（默认：<workspace>/.mini-coding-agent/hooks.yaml）。",
    )
    parser.add_argument(
        "--no-trace-display",
        action="store_true",
        help="关闭终端逐步 trace 行（覆盖 hooks.yaml）。",
    )
    parser.add_argument(
        "--no-session-trace",
        action="store_true",
        help="关闭 session 内 tool_trace JSON（覆盖 hooks.yaml）。",
    )
    parser.add_argument(
        "--no-shell-audit",
        action="store_true",
        help="关闭 run_shell 模式审计 Hook（覆盖 hooks.yaml）。",
    )
    # Phase 3: 强制「先规划再动手」；门控在 agent._execute_tool_after_validation（不替代 --approval）
    parser.add_argument(
        "--plan-first",
        action="store_true",
        help="每条 ask() 须先成功 make_plan，再允许 write_file、patch_file、run_shell。",
    )
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    # 初始化Agent
    agent = build_agent(args)
    # 打印欢迎界面
    print(build_welcome(agent, model=args.model, host=args.host))

    # 命令行后面跟的话 = 单次任务；不跟 = 进交互对话循环。
    # 有命令行任务 → 一次性模式（one-shot）
    if args.prompt:
        prompt = " ".join(args.prompt).strip()
        if prompt:
            print()
            try:
                print(agent.ask(prompt))
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 1
        return 0

    # REPL模式
    while True:
        try:
            user_input = input("\nmini-coding-agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0

        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            return 0
        if user_input == "/help":
            print(HELP_DETAILS)
            continue
        if user_input == "/memory":
            print(agent.memory_text())
            continue
        if user_input == "/session":
            print(agent.session_path)
            continue
        if user_input == "/reset":
            agent.reset()
            print("会话已重置")
            continue

        print()
        try:
            print(agent.ask(user_input))
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
