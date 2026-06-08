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


def _extract_quoted_json_field(body, field):
    """从 tool JSON 正文中提取字符串字段（容忍值内含单引号 / f-string 花括号）。"""
    pattern = rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    match = re.search(pattern, body)
    if not match:
        return None
    return bytes(match.group(1), "utf-8").decode("unicode_escape")


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
        path = _extract_quoted_json_field(text, "path")
        old_text = _extract_quoted_json_field(text, "old_text")
        new_text = _extract_quoted_json_field(text, "new_text")
        if path and old_text is not None and new_text is not None:
            return {"name": name, "args": {"path": path, "old_text": old_text, "new_text": new_text}}
    if name == "write_file":
        path = _extract_quoted_json_field(text, "path")
        content = _extract_quoted_json_field(text, "content")
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


# 解析模型返回的结果
def parse(raw):
    raw = str(raw)
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
