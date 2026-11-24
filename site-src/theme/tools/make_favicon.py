#!/usr/bin/env python3
"""Draw assets/brand/favicon.png (32x32): the three-dot mark.

Reads the signal colours from the dark set in assets/tokens.css. Needs Pillow
(tools/requirements.txt). Run from anywhere; nothing here is copied into a site.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCALE = 8  # supersample, then downscale for smooth edges


def signal_colours() -> list[str]:
    css = (ASSETS / "tokens.css").read_text()
    block = css.split("}", 1)[0]  # first rule: the dark set
    out = []
    for name in ("red", "amber", "green"):
        m = re.search(rf"--rig-signal-{name}:\s*(#[0-9a-fA-F]{{6}})\s*;", block)
        if not m:
            raise SystemExit(f"--rig-signal-{name} not found in dark set of tokens.css")
        out.append(m.group(1))
    return out


def main() -> None:
    size = 32 * SCALE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = 4.4 * SCALE
    for cx, colour in zip((5, 16, 27), signal_colours()):
        c = cx * SCALE
        y = 16 * SCALE
        draw.ellipse((c - r, y - r, c + r, y + r), fill=colour)
    img.resize((32, 32), Image.LANCZOS).save(ASSETS / "brand" / "favicon.png")


if __name__ == "__main__":
    main()
