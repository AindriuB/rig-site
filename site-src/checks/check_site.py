#!/usr/bin/env python3
"""Guards over the built site tree at $RIG_SITE_TREE. Stdlib only.

Prints to stderr one `path: message` line per failure; exits 1 on any failure.
"""
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

PATTERN = re.compile(
    r"fonts\.googleapis|fonts\.gstatic|googletagmanager|google-analytics"
    r"|gtag|unpkg|jsdelivr|cdnjs"
)
_URLISH = r"[A-Za-z0-9@._~:/%+-]*"
TOKEN = re.compile(_URLISH + "(?:" + PATTERN.pattern + ")" + _URLISH)
BUNDLE = re.compile(r"(?:^|/)assets/javascripts/bundle\.[0-9a-f]+\.min\.js(?:\.map)?$")
KNOWN_MAP_PROSE = re.compile(
    r"polyfill is automatically downloaded from unpkg\.com\. This is also compatible"
)
EXPECTED = {
    "https://unpkg.com/mermaid@11/dist/mermaid.min.js",
    "https://unpkg.com/resize-observer-polyfill",
}
PLANNING_NAMES = {
    "history", "history-index", "plan", "conventions", "architecture",
    "workflow", "release",
}
EXTERNAL_RE = re.compile(r"^\s*(?:[A-Za-z][A-Za-z0-9+.-]*:|//)")
VERSION = re.compile(r"^(?:v?\d+(?:\.\d+)*|latest|dev|stable)$")


class _External:
    """Match a URL the way a browser reads it: tab/newline stripped, backslash is slash."""

    @staticmethod
    def match(value):
        v = re.sub(r"[\t\n\r]", "", value).replace("\\", "/")
        return EXTERNAL_RE.match(v)


EXTERNAL = _External()


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems = []

    def handle_starttag(self, tag, attrs):
        a = {}
        for k, v in attrs:
            a.setdefault(k, v)
        if tag == "script":
            src = a.get("src")
            if src is not None:
                if EXTERNAL.match(src):
                    self.problems.append(f"script src is external: {src}")
                if "mermaid" in src.lower():
                    self.problems.append(f"script src mentions mermaid: {src}")
        elif tag == "link":
            rel = (a.get("rel") or "").lower().split()
            href = a.get("href")
            if "stylesheet" in rel and href is not None and EXTERNAL.match(href):
                self.problems.append(f"stylesheet href is external: {href}")
        elif tag == "img":
            alt = a.get("alt")
            decorative = alt == "" and (a.get("aria-hidden") or "").strip().lower() == "true"
            if not (alt or "").strip() and not decorative:
                self.problems.append(f"img without alt: {a.get('src', '')}")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def check_path(rel):
    parts = rel.split("/")
    out = []
    for p in parts:
        if p == "plan":
            out.append("excluded path segment 'plan'")
        if p.startswith("phase-"):
            out.append(f"excluded path segment '{p}' starts with 'phase-'")
    inside_docs = len(parts) >= 3 and parts[0] == "docs" and bool(VERSION.match(parts[1]))
    if not inside_docs:
        for p in parts:
            stem = p.rsplit(".", 1)[0] if "." in p else p
            if stem.lower() in PLANNING_NAMES:
                out.append(f"planning page '{p}' leaked into the site")
    return out


def main():
    tree = os.environ.get("RIG_SITE_TREE")
    if not tree or not Path(tree).is_dir():
        print(f"RIG_SITE_TREE: unset or not a directory: {tree!r}", file=sys.stderr)
        return 1
    root = Path(tree)
    fails = []
    bundle_tokens = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        for m in check_path(rel):
            fails.append(f"{rel}: {m}")
        if not path.is_file():
            continue
        text = path.read_bytes().decode("latin-1")
        if BUNDLE.search(rel):
            if rel.endswith(".map"):
                text = KNOWN_MAP_PROSE.sub("", text)
            d = rel.rsplit("/", 1)[0]
            bundle_tokens.setdefault(d, set()).update(
                m.group(0) for m in TOKEN.finditer(text)
            )
        else:
            for m in sorted({m.group(0) for m in PATTERN.finditer(text)}):
                fails.append(f"{rel}: third-party reference '{m}'")
        if path.suffix.lower() in (".html", ".htm"):
            if 'class="mermaid"' in text:
                fails.append(f'{rel}: contains class="mermaid"')
            if "language-mermaid" in text:
                fails.append(f"{rel}: contains language-mermaid")
            page = Page()
            page.feed(text)
            for p in page.problems:
                fails.append(f"{rel}: {p}")
    for d, toks in sorted(bundle_tokens.items()):
        if toks != EXPECTED:
            fails.append(
                f"{d}: Material bundle third-party references {sorted(toks)} "
                f"are not exactly the two expected unpkg strings"
            )
    for f in fails:
        print(f, file=sys.stderr)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
