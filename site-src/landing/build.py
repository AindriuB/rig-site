"""Build the landing page: resolve includes and captures, concatenate CSS, copy assets.

Usage: python site-src/landing/build.py --out <dir>
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME_ASSETS = HERE.parent / "theme" / "assets"

INCLUDE = re.compile(r"<!--\s*include:\s*([A-Za-z0-9_-]+)\s*-->")
CAPTURE = re.compile(r"\{\{capture:([A-Za-z0-9_-]+)\}\}")


class BuildError(Exception):
    pass


def _capture_name(stem: str) -> str:
    return re.sub(r"^\d+-", "", stem)


def load_captures(src: Path) -> dict:
    caps = {}
    for p in sorted((src / "captures").glob("*.txt")):
        caps[_capture_name(p.stem)] = p.read_text(encoding="utf-8")
    return caps


def render_page(src: Path) -> str:
    page = (src / "index.html").read_text(encoding="utf-8")
    partials = {p.stem: p for p in (src / "partials").glob("*.html")}
    captures = load_captures(src)
    used = set()

    def include(m):
        name = m.group(1)
        if name not in partials:
            raise BuildError(f"include '{name}' has no partial")
        used.add(name)
        return partials[name].read_text(encoding="utf-8")

    page = INCLUDE.sub(include, page)
    unused = sorted(set(partials) - used)
    if unused:
        raise BuildError("partial(s) no marker uses: " + ", ".join(unused))

    def capture(m):
        name = m.group(1)
        if name not in captures:
            raise BuildError(f"capture '{name}' not found")
        return html.escape(captures[name].rstrip("\n"), quote=False)

    return CAPTURE.sub(capture, page)


def render_css(src: Path) -> str:
    styles = src / "styles"
    files = [styles / "base.css"] + [p for p in sorted(styles.glob("*.css")) if p.name != "base.css"]
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def build(out: Path, src: Path = HERE) -> None:
    page = render_page(src)
    css = render_css(src)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    land = out / "assets" / "landing"
    land.mkdir(parents=True, exist_ok=True)
    (land / "landing.css").write_text(css, encoding="utf-8")
    shutil.copyfile(src / "landing.js", land / "landing.js")
    theme = out / "assets" / "theme"
    if theme.exists():
        shutil.rmtree(theme)
    shutil.copytree(THEME_ASSETS, theme)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        build(Path(args.out))
    except BuildError as e:
        print(f"build.py: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
