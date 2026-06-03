"""模型推理等待指示：阻塞式 complete() 期间向 stderr 输出单行 spinner。"""

import sys
import threading

# 用户可见文案（中文）
MESSAGE_MODEL = "正在等待模型响应…"
MESSAGE_PLAN = "正在生成任务规划…"
_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_REFRESH_INTERVAL = 0.1

_enabled = True


def set_wait_display_enabled(enabled: bool) -> None:
    """测试或脚本可关闭等待指示，避免 FakeModelClient 与 spinner 线程干扰。"""
    global _enabled
    _enabled = enabled


def is_wait_display_enabled() -> bool:
    return _enabled


def _stderr_is_tty() -> bool:
    try:
        return sys.stderr.isatty()
    except (AttributeError, ValueError):
        return False


class WaitDisplay:
    """上下文管理器：进入时显示等待指示，退出时清除 TTY 上的 spinner 行。"""

    def __init__(self, message: str = MESSAGE_MODEL):
        self.message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tty = False

    def __enter__(self):
        if not _enabled:
            return self
        self._tty = _stderr_is_tty()
        if self._tty:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            # 非 TTY：单行静态提示，不做 \r 动画
            print(self.message, file=sys.stderr, flush=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not _enabled:
            return False
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._tty:
            self._clear_line()
        return False

    def _spin(self):
        index = 0
        while not self._stop.wait(_REFRESH_INTERVAL):
            frame = _SPINNER_FRAMES[index % len(_SPINNER_FRAMES)]
            sys.stderr.write(f"\r{frame} {self.message}")
            sys.stderr.flush()
            index += 1

    def _clear_line(self):
        # 清除 spinner 行，避免污染后续 stderr trace 行
        width = len(self.message) + 4
        sys.stderr.write("\r" + " " * width + "\r")
        sys.stderr.flush()


def complete_with_wait_display(model_client, prompt, max_new_tokens, *, message: str = MESSAGE_MODEL):
    """包装 model_client.complete()，等待期间显示 stderr 指示。"""
    with WaitDisplay(message):
        return model_client.complete(prompt, max_new_tokens)
