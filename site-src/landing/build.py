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


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        raise BuildError(f"{path}: cannot read: {e.strerror or e}") from e


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def load_captures(src: Path) -> dict:
    caps = {}
    for p in sorted((src / "captures").glob("*.txt")):
        caps[_capture_name(p.stem)] = _read(p)
    return caps


def render_page(src: Path) -> str:
    index = src / "index.html"
    page = _read(index)
    partials = {p.stem: p for p in (src / "partials").glob("*.html")}
    captures = load_captures(src)
    used = set()

    def fill_captures(text: str, path: Path, whole: str, base: int = 0) -> str:
        def capture(m):
            name = m.group(1)
            if name not in captures:
                raise BuildError(f"{path}:{_line(whole, base + m.start())}: capture '{name}' not found")
            return html.escape(captures[name].rstrip("\n"), quote=False)

        return CAPTURE.sub(capture, text)

    def either(m):
        if m.group("inc") is None:
            return fill_captures(m.group(0), index, page, m.start())
        name = m.group("inc")
        if name not in partials:
            raise BuildError(f"{index}:{_line(page, m.start())}: include '{name}' has no partial")
        used.add(name)
        text = _read(partials[name])
        return fill_captures(text, partials[name], text)

    both = re.compile(INCLUDE.pattern.replace("([A-Za-z0-9_-]+)", "(?P<inc>[A-Za-z0-9_-]+)") + "|" + CAPTURE.pattern)
    out = both.sub(either, page)
    unused = sorted(set(partials) - used)
    if unused:
        names = ", ".join(str(partials[n]) for n in unused)
        raise BuildError(f"{src / 'partials'}: partial(s) no marker in {index} uses: {names}")
    return out


def render_css(src: Path) -> str:
    styles = src / "styles"
    base = styles / "base.css"
    files = [base] + [p for p in sorted(styles.glob("*.css")) if p.name != "base.css"]
    return "\n".join(_read(p) for p in files)


def build(out: Path, src: Path = HERE) -> None:
    page = render_page(src)
    css = render_css(src)
    js = src / "landing.js"
    if not js.is_file():
        raise BuildError(f"{js}: not found")
    if not THEME_ASSETS.is_dir():
        raise BuildError(f"{THEME_ASSETS}: theme assets directory not found")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    land = out / "assets" / "landing"
    land.mkdir(parents=True, exist_ok=True)
    (land / "landing.css").write_text(css, encoding="utf-8")
    shutil.copyfile(js, land / "landing.js")
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
