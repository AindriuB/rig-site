"""Generate the nav list from the pages in a docs dir."""
from __future__ import annotations

import re
from pathlib import Path

FIRST = ["workflows.md", "design.md", "release.md"]


def _plain(heading: str) -> str:
    t = re.sub(r"\s*\{[^}]*\}\s*$", "", heading)
    t = re.sub(r"\s+#+\s*$", "", t)
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"`+([^`]*)`+", r"\1", t)
    t = re.sub(r"(\*\*|__|\*|(?<!\w)_|_(?!\w))", "", t)
    t = re.sub(r"\\(.)", r"\1", t)
    return t.strip()


def page_title(path: Path) -> str:
    fence = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if m:
            fence = None if fence and line.strip().startswith(fence) else (fence or m.group(1))
            continue
        if fence is None and line.startswith("# "):
            return _plain(line[2:])
    return path.stem


def build_nav(docs_dir: Path) -> list[dict[str, str]]:
    names = sorted(p.name for p in docs_dir.glob("*.md"))
    ordered = [n for n in ["index.md", *FIRST] if n in names]
    ordered += [n for n in names if n not in ordered]
    return [{("Overview" if n == "index.md" else page_title(docs_dir / n)): n}
            for n in ordered]
