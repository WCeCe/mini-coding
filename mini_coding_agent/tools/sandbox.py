"""工作区路径沙箱：resolve_path / path_is_within_root。"""

from pathlib import Path


def path_is_within_root(root, resolved):
    probe = resolved
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    for candidate in (probe, *probe.parents):
        try:
            if candidate.samefile(root):
                return True
        except OSError:
            continue
    return False


def resolve_path(root, raw_path):
    path = Path(raw_path)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve()
    if not path_is_within_root(root, resolved):
        raise ValueError(f"路径超出工作区：{raw_path}")
    return resolved
