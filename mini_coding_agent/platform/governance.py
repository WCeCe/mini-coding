"""Phase 1 变更治理：diff、checkpoint、approve、回滚（write_file / patch_file 专用链）。"""

import json
import uuid

from mini_coding_agent.platform.util import (
    atomic_write_text,
    build_unified_diff,
    diff_summary,
    file_sha256,
    now,
    text_sha256,
)


# 处理写文件和patch文件的治理主流程
def run_governed_file_tool(agent, name, args):
    agent._last_tool_meta = {}
    path = agent.path(args["path"])
    rel_path = str(path.relative_to(agent.root))
    # 查看文件是否存在，在后续回溯的时候，如果存在，则恢复内容，如果不存在则直接删除
    existed = path.is_file()
    before = path.read_text(encoding="utf-8") if existed else ""
    # 执行write_file或patch_file，得到proposed content。这里的before其实是整个text文本内容
    proposed = proposed_file_content(name, args, before)
    # 计算diff，也就是计算这次tool的改动和上一次的改动之间的差异
    diff_text = build_unified_diff(rel_path, before, proposed)
    # 查询git状态，如果有未提交的更改，则返回警告
    git_warning = agent.workspace.git_dirty_warning()
    # 受理并输出，用户进行审批，如果审批不通过，则返回错误
    if not approve(
        name,
        args,
        read_only=agent.read_only,
        approval_policy=agent.approval_policy,
        diff=diff_text,
        git_warning=git_warning,
    ):
        return f"错误：{name} 审批被拒绝"

    # 只有write文件和patch文件需要保存checkpoint，其他工具不需要
    checkpoint = {
        # 每一个治理的唯一id
        "id": "cp-" + uuid.uuid4().hex[:12],
        "session_id": agent.session["id"],
        "tool_name": name,
        "path": rel_path,
        # 文件是否存在，以便后续恢复还是删除
        "existed": existed,
        # 恢复的文件内容，如果存在则返回，不存在则返回None
        "content": before if existed else None,
        # 文件内容的sha256值，如果存在则返回，不存在则返回None
        "sha256_before": text_sha256(before) if existed else None,
        "created_at": now(),
    }
    try:
        # 存到磁盘
        agent.checkpoint_store.save(checkpoint)
    except Exception as exc:
        return f"错误：{name} 检查点保存失败：{exc}"

    # 记录治理的附加信息,主要用于审计，后面通过record方法记录到session里面
    agent._last_tool_meta = {
        # diff的摘要
        "diff_summary": diff_summary(diff_text),
        "checkpoint_id": checkpoint["id"],
        # 是否回滚标识
        "rolled_back": False,
    }
    try:
        # 原子写入文件，如果失败则回滚
        atomic_write_text(path, proposed)
    except Exception as exc:
        rollback = restore_checkpoint(agent.root, checkpoint)
        agent._last_tool_meta["rolled_back"] = True
        return f"错误：工具 {name} 执行失败：{exc}; {rollback}"

    if name == "write_file":
        return f"已写入 {rel_path}（{len(proposed)} 字符）"
    return f"已修补 {rel_path}"


# 如果是write_file，直接返回要写的内容，如果不是，那么就是patch_file，则替换旧内容为新内容，返回全部的text文本
def proposed_file_content(name, args, before):
    if name == "write_file":
        return str(args["content"])
    old_text = str(args.get("old_text", ""))
    return before.replace(old_text, str(args["new_text"]), 1)


# 回滚
def restore_checkpoint(root, checkpoint):
    path = root / checkpoint["path"]
    # 如果文件不存在，则直接删除
    if not checkpoint["existed"]:
        if path.exists():
            path.unlink()
        return "已回滚：已删除新建文件"
    current_hash = file_sha256(path)
    before_hash = checkpoint["sha256_before"]
    # 计算两者是否一样，不一样则跳过回滚，因为文件已被外部修改，无法恢复
    if current_hash is not None and before_hash is not None and current_hash != before_hash:
        return "回滚已跳过：文件已被外部修改"
    # 恢复文件内容
    atomic_write_text(path, checkpoint["content"])
    return "已回滚：已恢复文件"


# 是否允许使用能修改你代码的工具（写、执行命令、替换)
def approve(name, args, *, read_only, approval_policy, diff=None, git_warning=None):
    if read_only:
        return False
    if approval_policy == "auto":
        return True
    if approval_policy == "never":
        return False
    try:
        if diff is not None:
            rel_path = str(args.get("path", ""))
            print(f"--- 变更预览：{name} {rel_path} ---")
            print(diff)
            print("--- 变更预览结束 ---")
        if git_warning:
            print(git_warning)
        if diff is not None:
            answer = input("批准此次变更？[y/n] ")
        # 因为diff是空，则有可能是其他risky工具，所以需要询问用户是否批准
        else:
            answer = input(f"批准 {name} {json.dumps(args, ensure_ascii=True)}？[y/n] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}
