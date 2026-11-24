#!/usr/bin/env python3
"""WCAG contrast check over rig's design tokens.

Run from the repo root, no arguments, no network:

    python3 site-src/checks/check_contrast.py

Reads site-src/theme/assets/tokens.css (or the path given as the one optional
argument, which the tests use) and checks, in both the dark and the light set:
text, muted text, link and accent at 4.5:1 on --rig-bg and --rig-surface;
--rig-on-accent at 4.5:1 on --rig-accent; each signal colour and --rig-border
at 3:1 on --rig-bg. One line per pair; exit 1 naming each failing pair.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TOKENS = Path(__file__).resolve().parent.parent / "theme" / "assets" / "tokens.css"

TEXT = 4.5
NON_TEXT = 3.0

PAIRS = (
    [(fg, bg, TEXT) for fg in ("text", "text-muted", "link", "accent") for bg in ("bg", "surface")]
    + [("on-accent", "accent", TEXT)]
    + [(fg, "bg", NON_TEXT) for fg in ("signal-red", "signal-amber", "signal-green", "border")]
)
REQUIRED = sorted({n for fg, bg, _ in PAIRS for n in (fg, bg)})

_DECL = re.compile(r"--rig-([a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;")


def parse_sets(css: str) -> dict[str, dict[str, str]]:
    """Return {'dark': {...}, 'light': {...}} from the first rule that sets
    --rig-bg for each: the :root/slate rule and the default-scheme rule."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # The @media fallback repeats the light set for pages with no Material
    # scheme; drop it so it cannot be read as a dark rule.
    css = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    sets: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, body = m.group(1), m.group(2)
        if "--rig-bg" not in body:
            continue
        if 'data-md-color-scheme="default"' in selector:
            key = "light"
        elif ":root" in selector or 'data-md-color-scheme="slate"' in selector:
            key = "dark"
        else:
            continue
        sets.setdefault(key, {}).update({n: v.lower() for n, v in _DECL.findall(body)})
    return sets


def luminance(hex_colour: str) -> float:
    chans = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def check(css: str) -> tuple[list[str], list[str]]:
    """Return (report lines, failures)."""
    sets = parse_sets(css)
    lines: list[str] = []
    fails: list[str] = []
    for scheme in ("dark", "light"):
        tokens = sets.get(scheme, {})
        for name in REQUIRED:
            if name not in tokens:
                fails.append(f"{scheme}: --rig-{name} missing")
        for fg, bg, minimum in PAIRS:
            if fg not in tokens or bg not in tokens:
                continue
            r = ratio(tokens[fg], tokens[bg])
            ok = r >= minimum
            label = f"{scheme}: --rig-{fg} on --rig-{bg}"
            lines.append(f"{'ok  ' if ok else 'FAIL'} {label} {r:.2f}:1 (need {minimum}:1)")
            if not ok:
                fails.append(f"{label} {r:.2f}:1 < {minimum}:1")
    return lines, fails


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else TOKENS
    lines, fails = check(path.read_text())
    print("\n".join(lines))
    if fails:
        print("\nFailing:", file=sys.stderr)
        print("\n".join(fails), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
