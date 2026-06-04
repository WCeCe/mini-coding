"""GL-3：format_error_for_model 与 verify retry 摘要。"""

from unittest.mock import patch

from mini_coding_agent.modes.graph.error_format import format_error_for_model
from mini_coding_agent.modes.graph.executor import execute_dag
from mini_coding_agent.modes.graph.planner import plan
from mini_coding_agent.modes.graph.types import NodeResult

from tests.test_harness_fix_bug_e2e import (
    TRACEBACK,
    _build_agent,
    _patch_tool,
)


def _long_pytest_output() -> str:
    noise = "\n".join(f"    frame_{i} = object()" for i in range(200))
    return f"""exit_code: 1
stdout:
============================= test session starts ==============================
collected 1 item

tests/test_calc.py F

=================================== FAILURES ===================================
{noise}
Traceback (most recent call last):
  File "/tmp/proj/tests/test_calc.py", line 42, in test_add
    assert add(1, 2) == 4
  File "/tmp/proj/calc.py", line 2, in add
    return a + c
NameError: name 'c' is not defined
stderr:
（空）"""


def _py_compile_message() -> str:
    return """py_compile 失败：
calc.py:   File "calc.py", line 2
    return a + c
         ^
SyntaxError: invalid syntax"""


def test_format_long_pytest_traceback_has_type_file_line():
    summary = format_error_for_model(_long_pytest_output())

    assert "NameError" in summary
    assert "calc.py" in summary
    assert "line" in summary or ":2" in summary or "42" in summary
    assert len(summary) <= 800
    assert "frame_199" not in summary
    assert summary.count("\n") + 1 <= 8


def test_format_py_compile_error_is_readable():
    summary = format_error_for_model(_py_compile_message())

    assert "calc.py" in summary
    assert "SyntaxError" in summary
    assert "invalid syntax" in summary
    assert "^" in summary or "return a + c" in summary
    assert len(summary) <= 800


def test_format_fallback_clips_unparseable_text():
    raw = "x" * 5000
    summary = format_error_for_model(raw)

    assert len(summary) <= 800 + 50
    assert "已截断" in summary


def test_verify_retry_prompt_uses_summary_not_full_log(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + c\n", encoding="utf-8")
    huge_log = _long_pytest_output()
    agent = _build_agent(
        tmp_path,
        [
            _patch_tool("return a + c", "return a +"),
            _patch_tool("return a +", "return a + b"),
        ],
    )
    dag = plan("fix_bug", user_message=TRACEBACK, workspace_root=tmp_path)
    verify_calls = {"n": 0}
    from mini_coding_agent.modes.graph.nodes import verify as verify_mod

    real_verify = verify_mod.run_verify

    def failing_then_ok(ctx):
        verify_calls["n"] += 1
        if verify_calls["n"] == 1:
            return NodeResult(ok=False, message=huge_log)
        return real_verify(ctx)

    with patch.dict(
        "mini_coding_agent.modes.graph.executor.NODE_RUNNERS",
        {"verify": failing_then_ok},
    ):
        result = execute_dag(agent, dag, TRACEBACK)

    assert result.ok
    assert len(agent.model_client.prompts) == 2
    second_prompt = agent.model_client.prompts[1]
    assert "上次验证失败" in second_prompt
    assert "NameError" in second_prompt
    assert "frame_199" not in second_prompt
    assert len(second_prompt) < len(huge_log)
