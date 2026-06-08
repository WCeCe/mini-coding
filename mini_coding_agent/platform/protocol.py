"""模型输出协议解析：parse / XML tool / retry 提示（纯函数，无 MiniAgent 依赖）。"""

import json
import re


def _json_tool_body_candidates(body):
    """生成 JSON tool 正文候选（容忍尾部多余 `}` 等常见模型笔误）。"""
    text = body.strip()
    if not text:
        return
    yield text
    trimmed = text.rstrip()
    while trimmed.endswith("}") and trimmed.count("{") < trimmed.count("}"):
        trimmed = trimmed[:-1].rstrip()
        yield trimmed


def _decode_json_string_literal(value: str) -> str:
    return bytes(value, "utf-8").decode("unicode_escape")


def _extract_quoted_json_field(body, field):
    """从 tool JSON 正文中提取字符串字段（容忍值内含单引号 / f-string 花括号）。"""
    pattern = rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    match = re.search(pattern, body)
    if not match:
        return None
    return _decode_json_string_literal(match.group(1))


def _extract_unclosed_json_string(body: str, field: str) -> str | None:
    """字段值缺少闭合引号时，扫描至 ``}}`` 或 ``"</tool>`` 前（容忍 f-string 内 ``{name}``）。"""
    marker = f'"{field}"'
    key_at = body.find(marker)
    if key_at == -1:
        return None
    colon = body.find(":", key_at + len(marker))
    if colon == -1:
        return None
    open_quote = body.find('"', colon + 1)
    if open_quote == -1:
        return None
    start = open_quote + 1
    i = start
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            i += 2
            continue
        if ch == '"':
            return _decode_json_string_literal(body[start:i])
        if body.startswith("}}", i) or body.startswith("}}</tool>", i):
            return _decode_json_string_literal(body[start:i])
        i += 1
    return None


def _extract_json_string_field(body: str, field: str) -> str | None:
    """提取 JSON 字符串字段；容忍 new_text 等缺少闭合引号（live syntaxerror_paren / nameerror_greet）。"""
    value = _extract_quoted_json_field(body, field)
    if value is not None:
        return value
    return _extract_unclosed_json_string(body, field)


def _unwrap_markdown_fences(text: str) -> str:
    """剥掉整段响应外层的 ``` / ```json 围栏（Phase 7.3）。"""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```\s*$", stripped, re.I)
    if match:
        return match.group(1).strip()
    return stripped


def _parse_tool_json_relaxed(body):
    """解析 <tool>{...}</tool> 内 JSON；标准 json.loads 失败时做有限容错。"""
    text = body.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    for candidate in _json_tool_body_candidates(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and str(payload.get("name", "")).strip():
            return payload

    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', text)
    if not name_match:
        return None
    name = name_match.group(1).strip()
    if name == "patch_file":
        path = _extract_json_string_field(text, "path")
        old_text = _extract_json_string_field(text, "old_text")
        new_text = _extract_json_string_field(text, "new_text")
        if path and new_text is not None:
            args = {"path": path, "new_text": new_text}
            if old_text is not None:
                args["old_text"] = old_text
            return {"name": name, "args": args}
    if name == "write_file":
        path = _extract_json_string_field(text, "path")
        content = _extract_json_string_field(text, "content")
        if path and content is not None:
            return {"name": name, "args": {"path": path, "content": content}}
    return None


def _normalize_tool_payload(payload):
    if not isinstance(payload, dict):
        return None
    if not str(payload.get("name", "")).strip():
        return None
    args = payload.get("args", {})
    if args is None:
        payload["args"] = {}
    elif not isinstance(args, dict):
        return None
    return payload


def _try_parse_bare_tool_json(raw: str):
    """围栏内或纯文本中的 {"name":...} tool JSON（无 <tool> 包装）。"""
    stripped = raw.strip()
    if not stripped.startswith("{") or '"name"' not in stripped:
        return None
    return _normalize_tool_payload(_parse_tool_json_relaxed(stripped))


# 解析模型返回的结果
def parse(raw):
    raw = _unwrap_markdown_fences(str(raw))
    # tool首先存在，并且tool的位置比final靠前
    if "<tool>" in raw and ("<final>" not in raw or raw.find("<tool>") < raw.find("<final>")):
        body = extract(raw, "tool")
        payload = _normalize_tool_payload(_parse_tool_json_relaxed(body))
        if payload is not None:
            return "tool", payload
        return "retry", retry_notice("模型返回的 tool JSON 格式错误")
    # tool首先存在，并且tool的位置比final靠前，且tool的格式是XML格式，类似这样：<tool name
    if re.search(r"<tool\s+\w", raw) and ("<final>" not in raw or raw.find("<tool") < raw.find("<final>")):
        payload = parse_xml_tool(raw)
        if payload is not None:
            return "tool", payload
        return "retry", retry_notice()
    bare = _try_parse_bare_tool_json(raw)
    if bare is not None:
        return "tool", bare
    if "<final>" in raw:
        final = extract(raw, "final").strip()
        if final:
            return "final", final
        return "retry", retry_notice("模型返回了空的 <final> 回答")
    raw = raw.strip()
    # 兜底，前面都没进入的话，说明模型返回的纯文本，没有tool、final，因此返回该文本
    if raw:
        return "final", raw
    return "retry", retry_notice("模型返回了空响应")


# （属于parse）用于生成一个提示模型重试的标准化错误消息
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


# （属于parse）解析XML格式的tool，返回想要使用的工具名称和参数（字典）
def parse_xml_tool(raw):
    match = re.search(r"<tool(?P<attrs>[^>]*)>(?P<body>.*?)</tool>", raw, re.S)
    if not match:
        return None
    # attrs 解析结果示例：{"name": "write_file", "path": "foo.py"}
    attrs = parse_attrs(match.group("attrs"))
    name = str(attrs.pop("name", "")).strip()
    if not name:
        return None
    # body 解析结果示例：<content>...</content>
    body = match.group("body")
    args = dict(attrs)
    # 遍历 body 中的 key，如果 key 在白名单中存在，则将key的值赋给 args[key]
    for key in ("content", "old_text", "new_text", "command", "task", "pattern", "path"):
        if f"<{key}>" in body:
            args[key] = extract_raw(body, key)
    body_text = body.strip("\n")
    if name == "write_file" and "content" not in args and body_text:
        args["content"] = body_text
    if name == "delegate" and "task" not in args and body_text:
        args["task"] = body_text.strip()
    return {"name": name, "args": args}


# （属于parse）parse_attrs 用正则找 key="value" 或 key='value'
def parse_attrs(text):
    attrs = {}
    for match in re.finditer(r"""([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""", text):
        attrs[match.group(1)] = match.group(2) if match.group(2) is not None else match.group(3)
    return attrs


# （属于parse）从文本中截取出指定 XML 风格标签（如 <tag>...</tag>）之间的内容，并去掉首尾空白字符。
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


# （属于parse）从文本中截取出指定 XML 风格标签（如 <tag>...</tag>）之间的内容，保留空白，跟源文本一字不差
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
