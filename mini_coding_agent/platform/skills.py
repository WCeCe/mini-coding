"""Phase 4：Skill 发现与两阶段加载辅助模块。

职责：
- 扫描 `<repo_root>/.mini-coding-agent/skills/*/SKILL.md`
- 解析 frontmatter（MVP：name、description）
- 提供 metadata 清单（阶段一）与正文读取（阶段二）

数据流（由 agent 调用）：
  启动/resume → SkillCatalog.scan → build_prefix 仅注入 metadata
  load_skill / CLI --skills → read_skill_body → memory.loaded_skills

与 make_plan 并列：Skill = 领域工作流包；plan = 单次任务拆分。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

SKILL_FILENAME = "SKILL.md"


@dataclass(frozen=True)
class SkillEntry:
    """单个 Skill 的 metadata 与磁盘路径（不含正文）。"""

    name: str
    description: str
    path: Path
    dir_name: str


class SkillCatalog:
    """启动时扫描 skills 目录；目录缺失或为空时不报错。"""

    def __init__(self, skills: dict[str, SkillEntry] | None = None):
        self._skills = dict(skills or {})

    @classmethod
    def scan(cls, repo_root: Path) -> tuple[SkillCatalog, list[str]]:
        """扫描 skills 目录；单个坏 Skill 跳过并收集 warn 消息。"""
        skills_root = Path(repo_root) / ".mini-coding-agent" / "skills"
        warnings: list[str] = []
        entries: dict[str, SkillEntry] = {}

        if not skills_root.is_dir():
            return cls({}), warnings

        for skill_dir in sorted(skills_root.iterdir(), key=lambda p: p.name.lower()):
            if not skill_dir.is_dir():
                continue
            skill_path = skill_dir / SKILL_FILENAME
            if not skill_path.is_file():
                continue
            entry, warn = parse_skill_file(skill_path, skill_dir.name)
            if warn:
                warnings.append(warn)
            if entry is None:
                continue
            if entry.name in entries:
                warnings.append(
                    f"Skill 名称重复 '{entry.name}'（{skill_path}）；跳过重复项"
                )
                continue
            entries[entry.name] = entry

        return cls(entries), warnings

    def names(self) -> list[str]:
        return sorted(self._skills.keys())

    def get(self, name: str) -> SkillEntry | None:
        return self._skills.get(str(name).strip())

    def metadata_block(self) -> str:
        """阶段一：仅 name + description，供 build_prefix 注入。"""
        if not self._skills:
            return "可用 Skill：无（`.mini-coding-agent/skills/` 为空或不存在）"
        lines = ["可用 Skill（仅 metadata；正文须 `load_skill` 或 CLI `--skills` 预加载）："]
        for name in self.names():
            entry = self._skills[name]
            desc = entry.description or "（无描述）"
            lines.append(f"- {name}: {desc}")
        lines.append(
            "规则：任务与某 Skill 相关时，先 `load_skill(name)` 加载正文，再按 Skill 指令执行"
            "（写文件等仍走 Phase 1 治理；与 `make_plan` 并列，不互相替代）。"
        )
        return "\n".join(lines)

    def read_body(self, name: str) -> tuple[str | None, str | None]:
        """读取 SKILL.md 正文（去 frontmatter）；失败返回 (None, 中文错误)。"""
        entry = self.get(name)
        if entry is None:
            known = "、".join(self.names()) or "（无）"
            return None, f"错误：未知 Skill '{name}'；可用：{known}"
        try:
            text = entry.path.read_text(encoding="utf-8")
        except OSError as exc:
            return None, f"错误：无法读取 Skill 文件 {entry.path.name}：{exc}"
        _meta, body, err = split_frontmatter(text)
        if err:
            return None, f"错误：Skill '{name}' frontmatter 无效：{err}"
        body = body.strip()
        if not body:
            return None, f"错误：Skill '{name}' 正文为空"
        return body, None


def parse_skill_file(path: Path, dir_name: str) -> tuple[SkillEntry | None, str | None]:
    """解析单个 SKILL.md；失败时 (None, warn)。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"Skill 无法读取（{path}）：{exc}；已跳过"

    meta, _body, err = split_frontmatter(text)
    if err:
        return None, f"Skill frontmatter 无效（{path}）：{err}；已跳过"

    name = str(meta.get("name", "")).strip() if meta else ""
    if not name:
        name = dir_name
    description = ""
    if meta and meta.get("description") is not None:
        description = str(meta.get("description", "")).strip()

    return SkillEntry(name=name, description=description, path=path, dir_name=dir_name), None


def split_frontmatter(text: str) -> tuple[dict | None, str, str | None]:
    """分离 YAML frontmatter 与正文；无 frontmatter 时 meta 为空 dict。"""
    raw = str(text)
    if not raw.startswith("---"):
        return {}, raw, None

    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw, None

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return None, raw, "缺少 closing ---"

    fm_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    if not fm_text.strip():
        return {}, body, None

    try:
        parsed = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        return None, body, str(exc)

    if parsed is None:
        return {}, body, None
    if not isinstance(parsed, dict):
        return None, body, "frontmatter 必须是 YAML 映射"
    return parsed, body, None


def loaded_skills_summary(loaded: dict) -> str:
    """memory_text / /memory 用的已加载 Skill 摘要。"""
    if not loaded:
        return "  - 无"
    lines = []
    for name in sorted(loaded.keys()):
        item = loaded[name]
        if isinstance(item, dict):
            desc = str(item.get("description", "")).strip() or "（无描述）"
            body = str(item.get("body", ""))
            char_count = len(body)
            lines.append(f"  - {name}: {desc}（{char_count} 字符）")
        else:
            lines.append(f"  - {name}")
    return "\n".join(lines)


def format_load_skill_result(name: str, description: str, body: str) -> str:
    """load_skill 工具成功返回：摘要 + 正文块。"""
    desc = description or "（无描述）"
    header = f"已加载 Skill '{name}'：{desc}（{len(body)} 字符）"
    return f"{header}\n\n<skill_body>\n{body}\n</skill_body>"


def emit_skill_warnings(warnings: list[str]) -> None:
    """单个坏 Skill / 预加载失败时 warn 到 stderr（参考 hooks 配置 warn 模式）。"""
    for message in warnings:
        print(f"[mini-agent] skills：{message}", file=sys.stderr)
