"""Brand mark: three dots on a track (task 16)."""

import importlib.util
import re
from pathlib import Path

from PIL import Image

THEME = Path(__file__).resolve().parent.parent
BRAND = THEME / "assets" / "brand"
CSS = (THEME / "assets" / "tokens.css").read_text()

_spec = importlib.util.spec_from_file_location(
    "check_contrast", THEME.parent / "checks" / "check_contrast.py"
)
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)
SETS = cc.parse_sets(CSS)
DARK = SETS["dark"]
HEXES = {v for v in DARK.values() if re.fullmatch(r"#[0-9a-f]{6}", v)}


def _svg(name):
    return (BRAND / name).read_text()


def _dots(svg):
    return re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="(#\w+)"', svg)


def _line(svg):
    m = re.search(r"<line ([^>]*)/>", svg)
    return dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))


def test_mark_svg():
    svg = _svg("mark.svg")
    for a in ('viewBox="0 0 48 16"', 'width="48"', 'height="16"', 'role="img"', 'aria-label="rig"'):
        assert a in svg
    assert svg.count("<line") == 1 and svg.index("<line") < svg.index("<circle")
    ln = _line(svg)
    assert (ln["x1"], ln["x2"], ln["y1"], ln["y2"]) == ("6", "42", "8", "8")
    assert ln["stroke-width"] == "2" and ln["stroke"] == DARK["border"]
    dots = _dots(svg)
    assert [d[0] for d in dots] == ["8", "24", "40"] and {d[1] for d in dots} == {"8"}
    assert len({d[2] for d in dots}) == 1 and 4 <= float(dots[0][2]) <= 5
    assert [d[3] for d in dots] == [DARK[f"signal-{n}"] for n in ("red", "amber", "green")]


def test_favicon_svg():
    svg = _svg("favicon.svg")
    assert 'viewBox="0 0 48 48"' in svg
    ln = _line(svg)
    assert ln["y1"] == ln["y2"] == "24" and 3 <= float(ln["stroke-width"]) <= 5
    assert ln["stroke"] == DARK["border"]
    dots = _dots(svg)
    assert len(dots) == 3 and len({d[2] for d in dots}) == 1 and 5 <= float(dots[0][2]) <= 7
    assert [d[3] for d in dots] == [DARK[f"signal-{n}"] for n in ("red", "amber", "green")]


def _nearest(px, cands):
    return min(cands, key=lambda k: sum((int(px[i]) - int(cands[k][i * 2 + 1 : i * 2 + 3], 16)) ** 2 for i in range(3)))


def test_favicon_png():
    img = Image.open(BRAND / "favicon.png")
    assert img.size == (32, 32) and img.mode == "RGBA"
    cands = {n: DARK[f"signal-{n}"] for n in ("red", "amber", "green")}
    cands["border"] = DARK["border"]
    for x, want in ((5, "red"), (16, "amber"), (27, "green")):
        assert _nearest(img.getpixel((x, 16)), cands) == want
    # track between the first two dots
    assert _nearest(img.getpixel((10, 16)), cands) == "border"
    assert _nearest(img.getpixel((11, 16)), cands) == "border"


def test_svg_colours_in_dark_set():
    for name in ("mark.svg", "favicon.svg"):
        lits = set(re.findall(r"#[0-9a-fA-F]{3,8}\b", _svg(name)))
        assert lits and {c.lower() for c in lits} <= HEXES


def test_track_contrast():
    track = DARK["border"]
    for scheme in ("light", "dark"):
        assert cc.ratio(track, SETS[scheme]["surface"]) >= 3
