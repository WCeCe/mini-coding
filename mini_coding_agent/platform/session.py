import json
from pathlib import Path


##############################
#### 5) Session Memory #######
##############################
# 存储到磁盘
class SessionStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # 获取session的文件路径
    def path(self, session_id):
        return self.root / f"{session_id}.json"

    # 将session写到磁盘中，返回path对象
    def save(self, session):
        path = self.path(session["id"])
        ## 把 session 写成 JSON 文件（真正落盘）
        path.write_text(json.dumps(session, indent=2), encoding="utf-8")
        return path

    # 从磁盘中加载session
    def load(self, session_id):
        return json.loads(self.path(session_id).read_text(encoding="utf-8"))

    # 获取最近一次的session_id
    def latest(self):
        files = sorted(self.root.glob("*.json"), key=lambda path: path.stat().st_mtime)
        return files[-1].stem if files else None


class CheckpointStore:
    # .mini-coding-agent/checkpoints/这里存储修改前的代码
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # 按session分目录，每个 checkpoint 一个 JSON 文件。
    # 分两级，session为第一级，checkpoint为第二级（tool级别，也就是代表这次tool的改动）
    def save(self, checkpoint):
        # .mini-coding-agent/checkpoints/20260529-abc123/
        session_dir = self.root / checkpoint["session_id"]
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / f"{checkpoint['id']}.json"
        path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
        return checkpoint
