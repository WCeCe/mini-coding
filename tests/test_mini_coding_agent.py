import json
import subprocess
import pytest
from unittest.mock import patch

from mini_coding_agent import (
    FakeModelClient,
    MiniAgent,
    OllamaModelClient,
    SessionStore,
    WorkspaceContext,
    build_welcome,
)
from mini_coding_agent.hooks.hook_config import HookConfig, load_hook_config
from mini_coding_agent.planning import PLAN_MAX_STEPS, parse_plan_response, validate_plan
from mini_coding_agent.skills import SkillCatalog


def build_workspace(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    return WorkspaceContext.build(tmp_path)


def build_agent(tmp_path, outputs, **kwargs):
    workspace = build_workspace(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    approval_policy = kwargs.pop("approval_policy", "auto")
    return MiniAgent(
        model_client=FakeModelClient(outputs),
        workspace=workspace,
        session_store=store,
        approval_policy=approval_policy,
        **kwargs,
    )


def test_agent_runs_tool_then_final(tmp_path):
    (tmp_path / "hello.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"read_file","args":{"path":"hello.txt","start":1,"end":2}}</tool>',
            "<final>Read the file successfully.</final>",
        ],
    )

    answer = agent.ask("Inspect hello.txt")

    assert answer == "Read the file successfully."
    assert any(item["role"] == "tool" and item["name"] == "read_file" for item in agent.session["history"])
    assert "hello.txt" in agent.session["memory"]["files"]


def test_agent_retries_after_empty_model_output(tmp_path):
    agent = build_agent(
        tmp_path,
        [
            "",
            "<final>Recovered after retry.</final>",
        ],
    )

    answer = agent.ask("Do the task")

    assert answer == "Recovered after retry."
    notices = [item["content"] for item in agent.session["history"] if item["role"] == "assistant"]
    assert any("空响应" in item for item in notices)


def test_agent_retries_after_malformed_tool_payload(tmp_path):
    (tmp_path / "hello.txt").write_text("alpha\n", encoding="utf-8")
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"read_file","args":"bad"}</tool>',
            '<tool>{"name":"read_file","args":{"path":"hello.txt","start":1,"end":1}}</tool>',
            "<final>Recovered after malformed tool output.</final>",
        ],
    )

    answer = agent.ask("Inspect hello.txt")

    assert answer == "Recovered after malformed tool output."
    assert any(item["role"] == "tool" and item["name"] == "read_file" for item in agent.session["history"])
    notices = [item["content"] for item in agent.session["history"] if item["role"] == "assistant"]
    assert any("有效的 <tool>" in item for item in notices)


def test_agent_accepts_xml_write_file_tool(tmp_path):
    agent = build_agent(
        tmp_path,
        [
            '<tool name="write_file" path="hello.py"><content>print("hi")\n</content></tool>',
            "<final>Done.</final>",
        ],
    )

    answer = agent.ask("Create hello.py")

    assert answer == "Done."
    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == 'print("hi")\n'


def test_retries_do_not_consume_the_whole_budget(tmp_path):
    agent = build_agent(
        tmp_path,
        [
            "",
            "",
            "<final>Recovered after several retries.</final>",
        ],
        max_steps=1,
    )

    answer = agent.ask("Do the task")

    assert answer == "Recovered after several retries."


def test_agent_saves_and_resumes_session(tmp_path):
    agent = build_agent(tmp_path, ["<final>First pass.</final>"])
    assert agent.ask("Start a session") == "First pass."

    resumed = MiniAgent.from_session(
        model_client=FakeModelClient(["<final>Resumed.</final>"]),
        workspace=agent.workspace,
        session_store=agent.session_store,
        session_id=agent.session["id"],
        approval_policy="auto",
    )

    assert resumed.session["history"][0]["content"] == "Start a session"
    assert resumed.ask("Continue") == "Resumed."


def test_delegate_uses_child_agent(tmp_path):
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"delegate","args":{"task":"inspect README","max_steps":2}}</tool>',
            "<final>Child result.</final>",
            "<final>Parent incorporated the child result.</final>",
        ],
    )

    answer = agent.ask("Use delegation")

    assert answer == "Parent incorporated the child result."
    tool_events = [item for item in agent.session["history"] if item["role"] == "tool"]
    assert tool_events[0]["name"] == "delegate"
    assert "delegate 结果" in tool_events[0]["content"]


def test_patch_file_replaces_exact_match(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello world\n", encoding="utf-8")
    agent = build_agent(tmp_path, [])

    result = agent.run_tool(
        "patch_file",
        {
            "path": "sample.txt",
            "old_text": "world",
            "new_text": "agent",
        },
    )

    assert result == "已修补 sample.txt"
    assert file_path.read_text(encoding="utf-8") == "hello agent\n"


def test_invalid_risky_tool_does_not_prompt_for_approval(tmp_path):
    agent = build_agent(tmp_path, [], approval_policy="ask")

    with patch("builtins.input") as mock_input:
        result = agent.run_tool("write_file", {})

    assert result.startswith("错误：write_file 参数无效：'path'")
    assert '示例：<tool name="write_file"' in result
    mock_input.assert_not_called()


def test_list_files_hides_internal_agent_state(tmp_path):
    agent = build_agent(tmp_path, [])
    (tmp_path / ".mini-coding-agent").mkdir(exist_ok=True)
    (tmp_path / ".git").mkdir(exist_ok=True)
    (tmp_path / "hello.txt").write_text("hi\n", encoding="utf-8")

    result = agent.run_tool("list_files", {})

    assert ".mini-coding-agent" not in result
    assert ".git" not in result
    assert "[F] hello.txt" in result


def test_path_rejects_parent_escape(tmp_path):
    agent = build_agent(tmp_path, [])

    with pytest.raises(ValueError, match="路径超出工作区"):
        agent.path("../outside.txt")


def test_path_rejects_symlink_escape(tmp_path):
    agent = build_agent(tmp_path, [])
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    link = tmp_path / "outside-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available in this environment")

    with pytest.raises(ValueError, match="路径超出工作区"):
        agent.path("outside-link/secret.txt")


def test_path_accepts_case_variant_on_case_insensitive_filesystems(tmp_path):
    project_root = tmp_path / "Proj"
    project_root.mkdir()
    agent = build_agent(project_root, [])
    variant = project_root.parent / project_root.name.lower() / "README.md"

    if not variant.exists():
        pytest.skip("case-sensitive filesystem")

    resolved = agent.path(str(variant))

    assert resolved.samefile(project_root / "README.md")


def test_repeated_identical_tool_call_is_rejected(tmp_path):
    agent = build_agent(tmp_path, [])
    agent.record({"role": "tool", "name": "list_files", "args": {}, "content": "(empty)", "created_at": "1"})
    agent.record({"role": "tool", "name": "list_files", "args": {}, "content": "(empty)", "created_at": "2"})

    result = agent.run_tool("list_files", {})

    assert result == "错误：连续两次相同调用 list_files；请换用其他工具或返回 <final>"


def test_welcome_screen_keeps_box_shape_for_long_paths(tmp_path):
    deep = tmp_path / "very" / "long" / "path" / "for" / "the" / "mini" / "agent" / "welcome" / "screen"
    deep.mkdir(parents=True)
    agent = build_agent(deep, [])

    welcome = build_welcome(agent, model="qwen3.5:4b", host="http://127.0.0.1:11434")
    lines = welcome.splitlines()

    assert len(lines) >= 5
    assert len({len(line) for line in lines}) == 1
    assert "..." in welcome
    assert "O   O" in welcome
    assert "MINI-CODING-AGENT" not in welcome
    assert "MINI CODING AGENT" in welcome
    assert "// READY" not in welcome
    assert "SLASH" not in welcome
    assert "READY      " not in welcome
    assert "commands: Commands:" not in welcome


def test_prompt_top_level_sections_stay_flush_left_with_multiline_content(tmp_path):
    workspace = WorkspaceContext(
        cwd=str(tmp_path),
        repo_root=str(tmp_path),
        branch="fix/prompt-indentation",
        default_branch="main",
        status=" M mini_coding_agent.py\n?? tests/test_prompt.py",
        recent_commits=["abc123 first commit", "def456 second commit"],
        project_docs={"README.md": "line1\nline2"},
    )
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    agent = MiniAgent(
        model_client=FakeModelClient([]),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
    )
    agent.session["memory"] = {
        "task": "verify prompt formatting",
        "files": ["mini_coding_agent.py"],
        "notes": ["saw inconsistent indentation", "need regression coverage"],
    }
    agent.record({"role": "user", "content": "inspect prompt()", "created_at": "1"})
    agent.record(
        {
            "role": "tool",
            "name": "read_file",
            "args": {"path": "mini_coding_agent.py"},
            "content": "    def prompt(self, user_message):\n        ...",
            "created_at": "2",
        }
    )

    prompt = agent.prompt("is this issue legit?")
    lines = prompt.splitlines()

    for label in ["规则：", "工具：", "有效响应示例：", "工作区：", "记忆：", "对话记录：", "当前用户请求："]:
        assert label in lines
        assert f"            {label}" not in prompt


def _make_filler(i):
    return {"role": "tool", "name": "list_files", "args": {}, "content": "", "created_at": str(i)}


def test_history_text_deduplicates_reads_but_not_after_write(tmp_path):
    """read_file deduplication must not skip a read that follows a write.

    Realistic prior-turn history (non-recent window):
        user: "update config"
        assistant: <tool>read_file config</tool>
        tool:   config v1 (content: setting=true)
        assistant: <tool>write_file config</tool>
        tool:   wrote
        assistant: <tool>read_file config</tool>
        tool:   config v2 (content: setting=false)   <- MUST NOT be skipped

    Without fix: seen_reads={"config"} after first read; write does NOT clear it;
                 second read is wrongly skipped (LLM sees stale content).
    With fix: write clears seen_reads, second read is correctly shown.
    """
    agent = build_agent(tmp_path, [])

    # Simulate a prior turn with read->write->read on the same file
    # history_length=13, recent_start=7 (indices 0-6 non-recent, 7-12 recent)
    agent.record({"role": "user", "content": "update config", "created_at": "0"})        # index 0
    agent.record({"role": "assistant", "content": '<tool>{"name":"read_file","args":{"path":"config.txt"}}</tool>', "created_at": "1"})
    agent.record({"role": "tool", "name": "read_file", "args": {"path": "config.txt"}, "content": "# config.txt\n   1: setting=true\n", "created_at": "2"})  # index 2, non-recent, ADDED
    agent.record({"role": "assistant", "content": '<tool>{"name":"write_file","args":{"path":"config.txt","content":"setting=false\n"}}</tool>', "created_at": "3"})
    agent.record({"role": "tool", "name": "write_file", "args": {"path": "config.txt", "content": "setting=false\n"}, "content": "wrote config.txt", "created_at": "4"})  # index 4, non-recent
    agent.record({"role": "assistant", "content": '<tool>{"name":"read_file","args":{"path":"config.txt"}}</tool>', "created_at": "5"})
    agent.record({"role": "tool", "name": "read_file", "args": {"path": "config.txt"}, "content": "# config.txt\n   1: setting=false\n", "created_at": "6"})  # index 6, non-recent, ADDED (write cleared dedup)
    # recent entries
    for i in range(7, 13):
        agent.record(_make_filler(i))

    history = agent.history_text()

    # Both read contents appear exactly once (check full line to avoid JSON false positives)
    assert "# config.txt\n   1: setting=true\n" in history
    assert "# config.txt\n   1: setting=false\n" in history
    # Also verify duplicate read (setting=true, same path) does NOT appear twice
    assert history.count("setting=true") == 1


def test_history_text_deduplicates_unchanged_repeated_reads(tmp_path):
    """read_file deduplication should still skip repeated reads with no write in between."""
    agent = build_agent(tmp_path, [])

    # Realistic: two identical reads with no write between them
    # history_length=10, recent_start=4 (indices 0-3 non-recent, 4-9 recent)
    agent.record({"role": "user", "content": "check logs", "created_at": "0"})  # index 0
    agent.record({"role": "assistant", "content": '<tool>{"name":"read_file","args":{"path":"log.txt"}}</tool>', "created_at": "1"})
    agent.record({"role": "tool", "name": "read_file", "args": {"path": "log.txt"}, "content": "# log.txt\n   1: stable\n", "created_at": "2"})  # index 2, non-recent, ADDED
    agent.record({"role": "assistant", "content": '<tool>{"name":"read_file","args":{"path":"log.txt"}}</tool>', "created_at": "3"})  # index 3, non-recent, SKIPPED (dup)
    for i in range(4, 10):
        agent.record(_make_filler(i))  # indices 4-9, recent

    history = agent.history_text()

    # Only first read should appear; duplicates must be skipped
    assert history.count("stable") == 1


def test_ollama_client_posts_expected_payload():
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"response": "<final>ok</final>"}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    client = OllamaModelClient(
        model="qwen3.5:4b",
        host="http://127.0.0.1:11434",
        temperature=0.2,
        top_p=0.9,
        timeout=30,
    )

    with patch("urllib.request.urlopen", fake_urlopen):
        result = client.complete("hello", 42)

    assert result == "<final>ok</final>"
    assert captured["url"] == "http://127.0.0.1:11434/api/generate"
    assert captured["timeout"] == 30
    assert captured["body"]["model"] == "qwen3.5:4b"
    assert captured["body"]["prompt"] == "hello"
    assert captured["body"]["stream"] is False
    assert captured["body"]["raw"] is False
    assert captured["body"]["think"] is False
    assert captured["body"]["options"]["num_predict"] == 42


def test_approval_denied_leaves_file_unchanged(tmp_path):
    target = tmp_path / "keep.txt"
    target.write_text("original\n", encoding="utf-8")
    agent = build_agent(tmp_path, [], approval_policy="never")

    result = agent.run_tool(
        "patch_file",
        {"path": "keep.txt", "old_text": "original", "new_text": "changed"},
    )

    assert result == "错误：patch_file 审批被拒绝"
    assert target.read_text(encoding="utf-8") == "original\n"


def test_write_file_records_diff_metadata(tmp_path):
    agent = build_agent(tmp_path, [], approval_policy="auto")

    result = agent.run_tool("write_file", {"path": "new.py", "content": "x = 1\n"})

    assert result == "已写入 new.py（6 字符）"
    assert (tmp_path / "new.py").read_text(encoding="utf-8") == "x = 1\n"
    assert agent._last_tool_meta["checkpoint_id"].startswith("cp-")
    assert "diff_summary" in agent._last_tool_meta
    assert agent._last_tool_meta["rolled_back"] is False


def test_ask_records_governance_metadata_in_history(tmp_path):
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"write_file","args":{"path":"tracked.py","content":"ok\\n"}}</tool>',
            "<final>Done.</final>",
        ],
        approval_policy="auto",
    )

    agent.ask("Write tracked.py")

    tool_events = [item for item in agent.session["history"] if item["role"] == "tool"]
    assert tool_events[-1]["checkpoint_id"].startswith("cp-")
    assert tool_events[-1]["rolled_back"] is False


def test_write_failure_rolls_back_new_file(tmp_path):
    agent = build_agent(tmp_path, [], approval_policy="auto")
    target = tmp_path / "fail.py"

    with patch("mini_coding_agent.governance.atomic_write_text", side_effect=OSError("disk full")):
        result = agent.run_tool("write_file", {"path": "fail.py", "content": "boom\n"})

    assert "错误：工具 write_file 执行失败" in result
    assert "已回滚：已删除新建文件" in result
    assert not target.exists()
    assert agent._last_tool_meta["rolled_back"] is True


def test_patch_failure_restores_original_content(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("hello world\n", encoding="utf-8")
    agent = build_agent(tmp_path, [], approval_policy="auto")

    with patch(
        "mini_coding_agent.governance.atomic_write_text",
        side_effect=[OSError("disk full"), None],
    ):
        result = agent.run_tool(
            "patch_file",
            {"path": "sample.txt", "old_text": "world", "new_text": "agent"},
        )

    assert "错误：工具 patch_file 执行失败" in result
    assert "已回滚：已恢复文件" in result
    assert target.read_text(encoding="utf-8") == "hello world\n"
    assert agent._last_tool_meta["rolled_back"] is True


def test_restore_skips_when_file_modified_externally(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("hello world\n", encoding="utf-8")
    agent = build_agent(tmp_path, [], approval_policy="auto")
    from mini_coding_agent import text_sha256

    checkpoint = {
        "id": "cp-test",
        "session_id": agent.session["id"],
        "tool_name": "patch_file",
        "path": "sample.txt",
        "existed": True,
        "content": "hello world\n",
        "sha256_before": text_sha256("hello world\n"),
        "created_at": "now",
    }
    target.write_text("user edited\n", encoding="utf-8")

    result = agent._restore_checkpoint(checkpoint)

    assert result == "回滚已跳过：文件已被外部修改"
    assert target.read_text(encoding="utf-8") == "user edited\n"


def test_approve_shows_diff_not_raw_json(tmp_path, capsys):
    target = tmp_path / "hello.txt"
    target.write_text("alpha\n", encoding="utf-8")
    agent = build_agent(tmp_path, [], approval_policy="ask")

    with patch("builtins.input", return_value="n"):
        agent.run_tool(
            "patch_file",
            {"path": "hello.txt", "old_text": "alpha", "new_text": "beta"},
        )

    captured = capsys.readouterr().out
    assert "--- 变更预览：" in captured
    assert "--- 变更预览结束 ---" in captured
    assert "-alpha" in captured or "+beta" in captured
    assert '"old_text"' not in captured


def test_git_dirty_warning_shown_on_approval(tmp_path, capsys):
    try:
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git not available")
    target = tmp_path / "dirty.txt"
    target.write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "add", "dirty.txt"], cwd=tmp_path, check=True, capture_output=True)
    target.write_text("b\n", encoding="utf-8")
    agent = build_agent(tmp_path, [], approval_policy="ask")

    with patch("builtins.input", return_value="n"):
        agent.run_tool("write_file", {"path": "other.py", "content": "x\n"})

    captured = capsys.readouterr().out
    assert "Git 警告" in captured


def test_run_shell_approval_unchanged(tmp_path):
    agent = build_agent(tmp_path, [], approval_policy="ask")

    with patch("builtins.input", return_value="n") as mock_input:
        result = agent.run_tool("run_shell", {"command": "echo hi", "timeout": 5})

    assert result == "错误：run_shell 审批被拒绝"
    prompt = mock_input.call_args.args[0]
    assert "批准 run_shell" in prompt
    assert "变更预览" not in prompt


def test_trace_hook_records_successful_tool(tmp_path):
    (tmp_path / "hello.txt").write_text("hi\n", encoding="utf-8")
    agent = build_agent(tmp_path, [])

    agent.run_tool("read_file", {"path": "hello.txt", "start": 1, "end": 1})

    trace = agent.session["tool_trace"]
    assert len(trace) == 1
    assert trace[0]["name"] == "read_file"
    assert trace[0]["success"] is True
    assert trace[0]["step"] == 1
    assert trace[0]["duration_ms"] >= 0


def test_trace_hook_records_failed_tool(tmp_path):
    agent = build_agent(tmp_path, [], approval_policy="never")

    agent.run_tool("write_file", {"path": "x.py", "content": "1\n"})

    trace = agent.session["tool_trace"]
    assert len(trace) == 1
    assert trace[0]["name"] == "write_file"
    assert trace[0]["success"] is False
    assert trace[0]["risky"] is True
    assert agent.session["tool_audit"]


def test_validation_error_does_not_emit_hooks(tmp_path):
    agent = build_agent(tmp_path, [])

    agent.run_tool("read_file", {})

    assert "tool_trace" not in agent.session or agent.session.get("tool_trace") == []


def test_register_custom_hook_observes_tool(tmp_path):
    agent = build_agent(tmp_path, [], enable_trace_hook=False)
    seen = []

    def pre(ctx):
        seen.append(("pre", ctx.name))

    def post(ctx):
        seen.append(("post", ctx.name, ctx.success))

    agent.register_hook("pre_tool", pre)
    agent.register_hook("post_tool", post)
    agent.run_tool("list_files", {})

    assert seen[0] == ("pre", "list_files")
    assert seen[1][0] == "post"
    assert seen[1][1] == "list_files"
    assert seen[1][2] is True


def test_hook_fail_open_continues_tool_execution(tmp_path):
    (tmp_path / "hello.txt").write_text("hi\n", encoding="utf-8")
    agent = build_agent(tmp_path, [], enable_trace_hook=False)

    def exploding_pre(_ctx):
        raise RuntimeError("hook failed")

    agent.register_hook("pre_tool", exploding_pre)
    result = agent.run_tool("read_file", {"path": "hello.txt", "start": 1, "end": 1})

    assert "hello.txt" in result


def test_governed_tool_emits_single_hook_pair(tmp_path):
    agent = build_agent(tmp_path, [], approval_policy="auto")
    pre_count = post_count = 0

    def count_pre(_ctx):
        nonlocal pre_count
        pre_count += 1

    def count_post(_ctx):
        nonlocal post_count
        post_count += 1

    agent.register_hook("pre_tool", count_pre)
    agent.register_hook("post_tool", count_post)
    agent.run_tool("write_file", {"path": "tracked.py", "content": "ok\n"})

    assert pre_count == 1
    assert post_count == 1
    assert len(agent.session["tool_trace"]) >= 1


def test_delegate_child_has_independent_trace(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"delegate","args":{"task":"read README","max_steps":2}}</tool>',
            '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":1}}</tool>',
            "<final>child done</final>",
            "<final>parent done</final>",
        ],
        approval_policy="auto",
    )

    answer = agent.ask("delegate task")

    assert answer == "parent done"
    parent_trace = agent.session.get("tool_trace", [])
    assert any(item["name"] == "delegate" for item in parent_trace)


def test_trace_display_prints_stderr_line(tmp_path, capsys):
    (tmp_path / "hello.txt").write_text("hi\n", encoding="utf-8")
    agent = build_agent(tmp_path, [])

    agent.run_tool("read_file", {"path": "hello.txt", "start": 1, "end": 1})

    captured = capsys.readouterr()
    assert "#1 read_file 成功" in captured.err
    assert "ms" in captured.err


def test_trace_display_disabled_via_hook_config(tmp_path, capsys):
    config = HookConfig(trace_display=False)
    agent = build_agent(tmp_path, [], hook_config=config)

    agent.run_tool("list_files", {})

    captured = capsys.readouterr()
    assert captured.err.strip() == ""
    assert len(agent.session["tool_trace"]) == 1


def test_session_trace_disabled_via_hook_config(tmp_path):
    config = HookConfig(session_trace=False, trace_display=False)
    agent = build_agent(tmp_path, [], hook_config=config)

    agent.run_tool("list_files", {})

    assert "tool_trace" not in agent.session or agent.session.get("tool_trace") == []


def test_shell_audit_warns_and_records_without_blocking(tmp_path, capsys):
    agent = build_agent(tmp_path, [], approval_policy="auto")
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    with patch("mini_coding_agent.tools.implementations.subprocess.run", return_value=completed):
        result = agent.run_tool("run_shell", {"command": "rm -rf /tmp/demo", "timeout": 5})

    assert "exit_code: 0" in result
    captured = capsys.readouterr()
    assert "shell 审计" in captured.err
    assert "rm -rf" in captured.err
    assert len(agent.session["shell_audit"]) == 1
    assert agent.session["shell_audit"][0]["pattern"] == "rm -rf"


def test_shell_audit_no_alert_for_safe_command(tmp_path, capsys):
    agent = build_agent(tmp_path, [], approval_policy="auto")
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="hi", stderr="")

    with patch("mini_coding_agent.tools.implementations.subprocess.run", return_value=completed):
        agent.run_tool("run_shell", {"command": "echo hi", "timeout": 5})

    captured = capsys.readouterr()
    assert "SHELL AUDIT" not in captured.err
    assert "shell_audit" not in agent.session


def test_yaml_missing_uses_defaults(tmp_path):
    config, warnings = load_hook_config(tmp_path / ".mini-coding-agent" / "hooks.yaml")

    assert warnings == []
    assert config.session_trace is True
    assert config.trace_display is True
    assert config.shell_audit is True


def test_yaml_malformed_fail_open(tmp_path):
    hooks_dir = tmp_path / ".mini-coding-agent"
    hooks_dir.mkdir(parents=True)
    hooks_path = hooks_dir / "hooks.yaml"
    hooks_path.write_text("{not: valid: yaml", encoding="utf-8")

    config, warnings = load_hook_config(hooks_path)

    assert config.session_trace is True
    assert any("无法读取" in item for item in warnings)


def test_yaml_disables_trace_display(tmp_path, capsys):
    hooks_dir = tmp_path / ".mini-coding-agent"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.yaml").write_text(
        "builtin_hooks:\n  trace_display: false\n  session_trace: true\n",
        encoding="utf-8",
    )
    agent = build_agent(tmp_path, [])

    agent.run_tool("list_files", {})

    captured = capsys.readouterr()
    assert "#1 list_files" not in captured.err
    assert len(agent.session["tool_trace"]) == 1


def test_cli_overrides_yaml_trace_display(tmp_path, capsys):
    hooks_dir = tmp_path / ".mini-coding-agent"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.yaml").write_text(
        "builtin_hooks:\n  trace_display: true\n",
        encoding="utf-8",
    )
    config, _ = load_hook_config(hooks_dir / "hooks.yaml")
    config.trace_display = False
    agent = build_agent(tmp_path, [], hook_config=config)

    agent.run_tool("list_files", {})

    captured = capsys.readouterr()
    assert "#1 list_files" not in captured.err


def _sample_plan(goal="ship feature"):
    return {
        "goal": goal,
        "steps": [
            {
                "id": "1",
                "title": "Survey codebase",
                "acceptance": "Key files identified",
                "risky_hint": "read_file",
            },
            {
                "id": "2",
                "title": "Implement change",
                "acceptance": "Tests pass",
                "risky_hint": "write_file",
            },
        ],
        "assumptions": ["Python project"],
        "out_of_scope": ["benchmark"],
    }


def test_make_plan_stores_structured_plan(tmp_path):
    plan_payload = json.dumps(_sample_plan("add logging"))
    agent = build_agent(tmp_path, [plan_payload])

    result = agent.run_tool("make_plan", {"goal": "add logging", "context": "read src first"})

    assert result.startswith("规划成功")
    assert "<plan_json>" in result
    assert agent.session["memory"]["plan"]["goal"] == "add logging"
    assert len(agent.session["memory"]["plan"]["steps"]) == 2
    assert agent.model_client.prompts[-1].startswith("你是 Mini-Coding-Agent 的任务规划助手")


def test_make_plan_rejects_empty_goal(tmp_path):
    agent = build_agent(tmp_path, [])

    result = agent.run_tool("make_plan", {"goal": "  "})

    assert "错误：" in result
    assert agent.session["memory"].get("plan") is None


def test_make_plan_invalid_json_does_not_update_memory(tmp_path):
    agent = build_agent(tmp_path, ["not json at all"])
    agent.session["memory"]["plan"] = {"goal": "old", "steps": [], "assumptions": [], "out_of_scope": []}

    result = agent.run_tool("make_plan", {"goal": "new goal"})

    assert "错误：make_plan 失败" in result
    assert agent.session["memory"]["plan"]["goal"] == "old"


def test_memory_text_includes_plan_summary(tmp_path):
    agent = build_agent(tmp_path, [json.dumps(_sample_plan())])
    agent.run_tool("make_plan", {"goal": "ship feature"})

    memory = agent.memory_text()

    assert "- plan:" in memory
    assert "ship feature" in memory
    assert "[1] Survey codebase" in memory


def test_plan_first_blocks_risky_tool_until_make_plan(tmp_path):
    agent = build_agent(tmp_path, [json.dumps(_sample_plan())], plan_first=True, approval_policy="auto")

    blocked = agent.run_tool("write_file", {"path": "blocked.py", "content": "x\n"})
    assert "make_plan" in blocked
    assert "--plan-first" in blocked
    assert not (tmp_path / "blocked.py").exists()

    agent.run_tool("make_plan", {"goal": "write blocked.py"})
    allowed = agent.run_tool("write_file", {"path": "blocked.py", "content": "x\n"})
    assert "已写入 blocked.py" in allowed
    assert (tmp_path / "blocked.py").exists()


def test_plan_first_off_allows_risky_without_plan(tmp_path):
    agent = build_agent(tmp_path, [], plan_first=False, approval_policy="auto")

    result = agent.run_tool("write_file", {"path": "free.py", "content": "ok\n"})

    assert "已写入 free.py" in result


def test_ask_plan_first_enforces_plan_before_write(tmp_path):
    plan_payload = json.dumps(_sample_plan("create hello.py"))
    agent = build_agent(
        tmp_path,
        [
            '<tool name="write_file" path="hello.py"><content>print("early")\n</content></tool>',
            '<tool>{"name":"make_plan","args":{"goal":"create hello.py"}}</tool>',
            plan_payload,
            '<tool name="write_file" path="hello.py"><content>print("ok")\n</content></tool>',
            "<final>Done.</final>",
        ],
        plan_first=True,
        approval_policy="auto",
    )

    answer = agent.ask("Create hello.py with plan-first")

    assert answer == "Done."
    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == 'print("ok")\n'
    tool_contents = [item["content"] for item in agent.session["history"] if item["role"] == "tool"]
    assert any("make_plan" in item and "--plan-first" in item for item in tool_contents)


def test_parse_plan_response_accepts_fenced_json():
    raw = 'Here is the plan:\n```json\n' + json.dumps(_sample_plan()) + "\n```"
    plan = parse_plan_response(raw)
    assert plan["goal"] == "ship feature"


def test_validate_plan_rejects_too_many_steps():
    steps = [
        {"id": str(i), "title": f"step {i}", "acceptance": "done"}
        for i in range(1, PLAN_MAX_STEPS + 2)
    ]
    plan = {"goal": "big", "steps": steps, "assumptions": [], "out_of_scope": []}
    with pytest.raises(ValueError, match="步骤过多"):
        validate_plan(plan)


def test_child_agent_has_make_plan_at_delegate_depth(tmp_path):
    """子 Agent（read_only, depth=1）仍有 make_plan；无 delegate（与 depth 策略一致）。"""
    child = MiniAgent(
        model_client=FakeModelClient([]),
        workspace=build_workspace(tmp_path),
        session_store=SessionStore(tmp_path / ".mini-coding-agent" / "sessions"),
        depth=1,
        max_depth=1,
        read_only=True,
        enable_trace_hook=False,
    )
    assert "make_plan" in child.tools
    assert "delegate" not in child.tools


def _write_skill(tmp_path, dir_name, *, name=None, description=None, body="# Skill Body\nstep 1\n", frontmatter_extra=""):
    """测试 fixture：写入 .mini-coding-agent/skills/<dir>/SKILL.md。"""
    skill_dir = tmp_path / ".mini-coding-agent" / "skills" / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_name = name if name is not None else dir_name
    fm_desc = description if description is not None else f"测试 Skill {dir_name}"
    lines = ["---", f"name: {fm_name}", f"description: {fm_desc}"]
    if frontmatter_extra:
        lines.append(frontmatter_extra)
    lines.extend(["---", "", body])
    (skill_dir / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
    return skill_dir


def test_skill_catalog_empty_when_dir_missing(tmp_path):
    catalog, warnings = SkillCatalog.scan(tmp_path)
    assert catalog.names() == []
    assert warnings == []


def test_skill_catalog_discovers_skills(tmp_path):
    _write_skill(tmp_path, "code-review", description="审查 PR")
    _write_skill(tmp_path, "deploy", description="部署流程")
    agent = build_agent(tmp_path, [])

    assert set(agent.skill_catalog.names()) == {"code-review", "deploy"}
    block = agent.skill_catalog.metadata_block()
    assert "code-review" in block
    assert "审查 PR" in block
    assert "load_skill" in block


def test_build_prefix_includes_skill_metadata_not_body(tmp_path):
    body = "# Secret\nDo not leak in prefix\n"
    _write_skill(tmp_path, "secret-skill", body=body)
    agent = build_agent(tmp_path, [])

    assert "Secret" not in agent.prefix
    assert "Do not leak" not in agent.prefix
    assert "secret-skill" in agent.prefix


def test_skill_catalog_skips_bad_frontmatter(tmp_path, capsys):
    skill_dir = tmp_path / ".mini-coding-agent" / "skills" / "broken"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\n{not: valid\n---\nbody\n", encoding="utf-8")
    _write_skill(tmp_path, "good-skill")

    agent = build_agent(tmp_path, [])
    captured = capsys.readouterr()

    assert agent.skill_catalog.names() == ["good-skill"]
    assert "frontmatter 无效" in captured.err


def test_load_skill_stores_body_in_memory(tmp_path):
    _write_skill(tmp_path, "code-review", body="# Review\n1. read diff\n")
    agent = build_agent(tmp_path, [])

    result = agent.run_tool("load_skill", {"name": "code-review"})

    assert result.startswith("已加载 Skill 'code-review'")
    assert "<skill_body>" in result
    assert "read diff" in result
    loaded = agent.session["memory"]["loaded_skills"]["code-review"]
    assert loaded["body"] == "# Review\n1. read diff"
    assert loaded["description"] == "测试 Skill code-review"


def test_load_skill_unknown_name_does_not_update_memory(tmp_path):
    _write_skill(tmp_path, "known")
    agent = build_agent(tmp_path, [])

    result = agent.run_tool("load_skill", {"name": "missing"})

    assert result.startswith("错误：未知 Skill")
    assert agent.session["memory"]["loaded_skills"] == {}


def test_load_skill_rejects_empty_name(tmp_path):
    agent = build_agent(tmp_path, [])

    result = agent.run_tool("load_skill", {"name": "  "})

    assert "错误：load_skill 参数无效" in result


def test_load_skill_reload_overwrites_body(tmp_path):
    _write_skill(tmp_path, "flow", body="# v1\n")
    agent = build_agent(tmp_path, [])
    agent.run_tool("load_skill", {"name": "flow"})
    (tmp_path / ".mini-coding-agent" / "skills" / "flow" / "SKILL.md").write_text(
        "---\nname: flow\ndescription: updated\n---\n\n# v2\n",
        encoding="utf-8",
    )

    result = agent.run_tool("load_skill", {"name": "flow"})

    assert "# v2" in result
    assert agent.session["memory"]["loaded_skills"]["flow"]["body"] == "# v2"


def test_memory_text_includes_loaded_skill_body(tmp_path):
    _write_skill(tmp_path, "memo-skill", body="# Memo Skill\nfollow steps\n")
    agent = build_agent(tmp_path, [])
    agent.run_tool("load_skill", {"name": "memo-skill"})

    memory = agent.memory_text()

    assert "- loaded_skills:" in memory
    assert "memo-skill" in memory
    assert "follow steps" in memory


def test_reset_clears_loaded_skills(tmp_path):
    _write_skill(tmp_path, "temp")
    agent = build_agent(tmp_path, [])
    agent.run_tool("load_skill", {"name": "temp"})
    assert agent.session["memory"]["loaded_skills"]

    agent.reset()

    assert agent.session["memory"]["loaded_skills"] == {}
    assert "无" in agent.memory_text()


def test_preload_skills_on_agent_init(tmp_path):
    _write_skill(tmp_path, "preload-a", body="# A\n")
    _write_skill(tmp_path, "preload-b", body="# B\n")
    agent = build_agent(tmp_path, [], preload_skills=["preload-a", "preload-b"])

    loaded = agent.session["memory"]["loaded_skills"]
    assert set(loaded.keys()) == {"preload-a", "preload-b"}
    assert "# A" in loaded["preload-a"]["body"]


def test_preload_unknown_skill_warns_but_keeps_known(tmp_path, capsys):
    _write_skill(tmp_path, "only-one", body="# OK\n")
    agent = build_agent(tmp_path, [], preload_skills=["only-one", "ghost"])
    captured = capsys.readouterr()

    assert "only-one" in agent.session["memory"]["loaded_skills"]
    assert "ghost" not in agent.session["memory"]["loaded_skills"]
    assert "ghost" in captured.err


def test_child_agent_has_load_skill(tmp_path):
    _write_skill(tmp_path, "shared")
    child = MiniAgent(
        model_client=FakeModelClient([]),
        workspace=build_workspace(tmp_path),
        session_store=SessionStore(tmp_path / ".mini-coding-agent" / "sessions"),
        depth=1,
        max_depth=1,
        read_only=True,
        enable_trace_hook=False,
    )
    assert "load_skill" in child.tools
    assert "shared" in child.skill_catalog.names()


@pytest.fixture
def restore_wait_display():
    from mini_coding_agent.wait_display import set_wait_display_enabled

    set_wait_display_enabled(True)
    yield
    set_wait_display_enabled(True)


def test_wait_display_non_tty_prints_static_message(tmp_path, capsys, restore_wait_display, monkeypatch):
    monkeypatch.setattr("mini_coding_agent.wait_display._stderr_is_tty", lambda: False)
    agent = build_agent(tmp_path, ["<final>你好。</final>"])

    answer = agent.ask("你好")

    assert answer == "你好。"
    captured = capsys.readouterr()
    assert captured.err.strip() == "正在等待模型响应…"
    assert "\r" not in captured.err


def test_wait_display_tty_clears_spinner_line(tmp_path, capsys, restore_wait_display, monkeypatch):
    import time

    class SlowFakeModelClient(FakeModelClient):
        def complete(self, prompt, max_new_tokens):
            time.sleep(0.25)
            return super().complete(prompt, max_new_tokens)

    monkeypatch.setattr("mini_coding_agent.wait_display._stderr_is_tty", lambda: True)
    agent = MiniAgent(
        model_client=SlowFakeModelClient(["<final>完成。</final>"]),
        workspace=build_workspace(tmp_path),
        session_store=SessionStore(tmp_path / ".mini-coding-agent" / "sessions"),
        approval_policy="auto",
    )

    answer = agent.ask("请回答")

    assert answer == "完成。"
    captured = capsys.readouterr()
    # capsys 会保留 TTY spinner 的中间帧；退出时 _clear_line 以 \r 覆写结尾
    assert "\r" in captured.err
    assert captured.err.endswith("\r")


def test_wait_display_during_make_plan(tmp_path, capsys, restore_wait_display, monkeypatch):
    monkeypatch.setattr("mini_coding_agent.wait_display._stderr_is_tty", lambda: False)
    plan_payload = json.dumps(_sample_plan("add logging"))
    agent = build_agent(tmp_path, [plan_payload])

    agent.run_tool("make_plan", {"goal": "add logging"})

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert lines[0] == "正在生成任务规划…"
    assert any("make_plan" in line for line in lines)


def test_wait_display_disabled_no_stderr(tmp_path, capsys, restore_wait_display, monkeypatch):
    from mini_coding_agent.wait_display import set_wait_display_enabled

    monkeypatch.setattr("mini_coding_agent.wait_display._stderr_is_tty", lambda: False)
    set_wait_display_enabled(False)
    agent = build_agent(tmp_path, ["<final>静默。</final>"])

    answer = agent.ask("你好")

    assert answer == "静默。"
    captured = capsys.readouterr()
    assert captured.err.strip() == ""


def test_wait_display_before_trace_display_order(tmp_path, capsys, restore_wait_display, monkeypatch):
    """模型返回后 spinner 行已清除，trace 行不被 spinner 残留污染。"""
    monkeypatch.setattr("mini_coding_agent.wait_display._stderr_is_tty", lambda: False)
    (tmp_path / "hello.txt").write_text("hi\n", encoding="utf-8")
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"read_file","args":{"path":"hello.txt","start":1,"end":1}}</tool>',
            "<final>已读取。</final>",
        ],
    )

    answer = agent.ask("读取 hello.txt")

    assert answer == "已读取。"
    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert lines[0] == "正在等待模型响应…"
    assert lines[1].startswith("[mini-agent] #1 read_file 成功")
    assert lines[2] == "正在等待模型响应…"
    assert all("\r" not in line for line in lines)

