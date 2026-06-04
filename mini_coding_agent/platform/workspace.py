import subprocess
from pathlib import Path

from mini_coding_agent.platform.constants import DOC_NAMES
from mini_coding_agent.platform.util import clip


##############################
#### 1) 工作区             ####
##############################
# Workspace:
# - cwd: ...
# - repo_root: ...
# - branch: ...
# - default_branch: ...
# - status:
#   （git status 的内容）
# - recent_commits:
#   - abc123 ...
#   - def456 ...
# - project_docs:
#   - README.md
#     （文件内容片段）
#   - pyproject.toml
#     （文件内容片段）
class WorkspaceContext:
    def __init__(self, cwd, repo_root, branch, default_branch, status, recent_commits, project_docs):
        # 当前工作目录
        self.cwd = cwd
        # 仓库根目录
        self.repo_root = repo_root
        # 当前分支
        self.branch = branch
        # 默认分支
        self.default_branch = default_branch
        # git status 的内容
        self.status = status
        # 最近5次提交
        self.recent_commits = recent_commits
        # 仓库中里面的DOC_NAMES里列出来的这四种文档
        self.project_docs = project_docs

    # 构建仓库快照对象
    @classmethod
    def build(cls, cwd):
        cwd = Path(cwd).resolve()

        # 1.获取git仓库的status等git信息
        def git(args, fallback=""):
            try:
                # subprocess.run(...)相当于在子进程里执行命令，类似你在终端敲 git 命令
                result = subprocess.run(
                    ["git", *args],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                    timeout=5,
                )
                # 终端打印出来的结果，或者fallback
                return result.stdout.strip() or fallback
            except Exception:
                return fallback

        # 获取仓库根目录，转为str
        repo_root = Path(git(["rev-parse", "--show-toplevel"], str(cwd))).resolve()
        # 本质获取仓库中里面的DOC_NAMES里列出来的这四种文档，然后写入到docs里面，但是如果一个文档超过了1200个字符，就会发生截断
        # 是按「每个文档文件」单独截断 1200，不是 4 个文件一共 1200
        docs = {}
        for base in (repo_root, cwd):
            for name in DOC_NAMES:
                path = base / name
                if not path.exists():
                    continue
                # 仓库根目录的相对路径relative
                key = str(path.relative_to(repo_root))
                if key in docs:
                    continue
                docs[key] = clip(path.read_text(encoding="utf-8", errors="replace"), 1200)

        return cls(
            cwd=str(cwd),
            repo_root=str(repo_root),
            branch=git(["branch", "--show-current"], "-") or "-",
            default_branch=(git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], "origin/main") or "origin/main").removeprefix(
                "origin/"
            ),
            status=clip(git(["status", "--short"], "clean") or "clean", 1500),
            recent_commits=[line for line in git(["log", "--oneline", "-5"]).splitlines() if line],
            project_docs=docs,
        )

    # 获取快照信息转为文本
    def text(self):
        commits = "\n".join(f"- {line}" for line in self.recent_commits) or "- 无"
        docs = "\n".join(f"- {path}\n{snippet}" for path, snippet in self.project_docs.items()) or "- 无"
        return "\n".join(
            [
                "工作区：",
                f"- cwd: {self.cwd}",
                f"- repo_root: {self.repo_root}",
                f"- branch: {self.branch}",
                f"- default_branch: {self.default_branch}",
                "- status:",
                self.status,
                "- recent_commits:",
                commits,
                "- project_docs:",
                docs,
            ]
        )

    # 在更改代码前，查询git状态，防止修改了用户没有提交的代码
    def refresh_git_status(self):
        repo_root = Path(self.repo_root)

        def git(args, fallback=""):
            try:
                result = subprocess.run(
                    ["git", *args],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                    timeout=5,
                )
                return result.stdout.strip() or fallback
            except Exception:
                return fallback

        # clean是fallback的默认值，如果返回成功但是为空，则也是clean
        status = git(["status", "--short"], "clean") or "clean"
        self.status = clip(status, 1500)
        return self.status

    # 如果git状态不为clean，则返回警告，告诉用户有未提交的修改
    def git_dirty_warning(self):
        status = self.refresh_git_status()
        if status.strip() in {"", "clean"}:
            return None
        return "Git 警告：工作区存在未提交的更改\n" + status
