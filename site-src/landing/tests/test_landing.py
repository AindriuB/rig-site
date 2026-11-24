import html
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

LANDING = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANDING))
import build  # noqa: E402

THEME = LANDING.parent / "theme" / "assets"


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("landing")
    build.build(d)
    return d


@pytest.fixture(scope="module")
def page(out):
    return (out / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css(out):
    return (out / "assets" / "landing" / "landing.css").read_text(encoding="utf-8")


def make_src(tmp_path, index, partials, styles=None):
    src = tmp_path / "src"
    (src / "partials").mkdir(parents=True)
    (src / "styles").mkdir()
    (src / "captures").mkdir()
    (src / "index.html").write_text(index)
    for n, t in partials.items():
        (src / "partials" / f"{n}.html").write_text(t)
    for n, t in (styles or {"base": ""}).items():
        (src / "styles" / f"{n}.css").write_text(t)
    (src / "landing.js").write_text("")
    return src


def test_cli_writes_contract_outputs(tmp_path):
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, str(LANDING / "build.py"), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for rel in ("index.html", "assets/landing/landing.css", "assets/landing/landing.js",
                "assets/theme/tokens.css", "assets/theme/brand/mark.svg"):
        assert (out / rel).is_file(), rel
    assert "<!-- include:" not in (out / "index.html").read_text()


def test_theme_assets_copied_exactly(out):
    for p in THEME.rglob("*"):
        if p.is_file():
            assert (out / "assets" / "theme" / p.relative_to(THEME)).read_bytes() == p.read_bytes()


def test_missing_partial_fails(tmp_path):
    src = make_src(tmp_path, "<!-- include: nope -->", {})
    with pytest.raises(build.BuildError):
        build.build(tmp_path / "o", src)


def test_unused_partial_fails(tmp_path):
    src = make_src(tmp_path, "<p>x</p>", {"extra": "<p>y</p>"})
    with pytest.raises(build.BuildError):
        build.build(tmp_path / "o", src)


def test_css_order_base_first_then_filename(tmp_path):
    src = make_src(tmp_path, "<p>x</p>", {}, {"zeta": "/*z*/", "base": "/*b*/", "alpha": "/*a*/"})
    assert build.render_css(src).split() == ["/*b*/", "/*a*/", "/*z*/"]


def test_stub_slots_present(page):
    for slot in ("push-panel", "forges", "state"):
        assert f'id="{slot}"' in page
        assert (LANDING / "styles" / f"{slot}.css").read_text() == ""


def test_links(page):
    for href in ('href="docs/"', 'href="docs/dev/"', 'href="changelog/"',
                 'href="https://github.com/AindriuB/rig"'):
        assert href in page
    for m in re.finditer(r'<a [^>]*href="([^"]*)"', page):
        h = m.group(1)
        assert h.startswith("https://github.com/AindriuB/") or not re.match(r"^(/|[a-z]+:)", h), h


def test_hero_stops_and_commands(page):
    svg = re.search(r'<svg class="hero-svg".*?</svg>', page, re.S).group(0)
    for label in ("todo", "in progress", "pushed", "PR", "CI", "green", "done",
                  "rig task new", "rig task start", "rig push", "rig pr open",
                  "rig pr wait", "exit 0", "rig task move", "&lt;task&gt; done"):
        assert f">{label}<" in svg, label
    assert svg.count("rig pr wait") >= 4  # two labels plus desc


def test_terminal_matches_captures(page):
    caps = sorted((LANDING / "captures").glob("*.txt"))
    assert len(caps) == 3
    cmds = []
    for p in caps:
        text = p.read_text()
        lines = text.splitlines()
        assert lines[0].startswith("$ rig ")
        m = re.fullmatch(r"# rig (\d+)\.(\d+)\.\d+, captured \d{4}-\d{2}-\d{2}", lines[1])
        assert m and (int(m.group(1)), int(m.group(2))) >= (0, 5), lines[1]
        assert html.escape(text.rstrip("\n"), quote=False) in page
        cmds.append(lines[0])
    assert [c.split()[2:4] for c in cmds] == [["push", "08"], ["pr", "wait"], ["task", "move"]]
    term = re.search(r'<div class="terminal".*?</div>\s*</section>', page, re.S).group(0)
    assert "<svg" not in term and "<canvas" not in term


def test_motion_only_in_no_preference_block(css):
    stripped = css
    while True:
        m = re.search(r"@media\s*\(prefers-reduced-motion:\s*no-preference\)\s*\{", stripped)
        if not m:
            break
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(stripped[i], 0)
            i += 1
        stripped = stripped[:m.start()] + stripped[i:]
    assert not re.search(r"\b(animation|transition)[\w-]*\s*:|@keyframes", stripped)
    assert "animation" in css  # the motion exists, just guarded


class _Svgs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.svgs, self.ids = [], [], {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "svg":
            self.svgs.append(a)
            self.stack.append(a)
        if "id" in a:
            self.ids[a["id"]] = tag
        if tag in ("title", "desc") and self.stack:
            self.stack[-1].setdefault("_kids", []).append((tag, a.get("id")))

    def handle_endtag(self, tag):
        if tag == "svg" and self.stack:
            self.stack.pop()


def test_svgs_accessible(page):
    p = _Svgs()
    p.feed(page)
    assert p.svgs
    for a in p.svgs:
        if a.get("aria-hidden") == "true":
            continue
        assert a.get("role") == "img"
        kids = dict((t, i) for t, i in a.get("_kids", []))
        assert set(kids) >= {"title", "desc"}
        assert set(a["aria-labelledby"].split()) == {kids["title"], kids["desc"]}


def test_nothing_external_loaded(page, css):
    for tag in re.finditer(r"<(script|img|link|iframe|source|video|audio)\b[^>]*>", page):
        for m in re.finditer(r'\b(?:src|href)="([^"]*)"', tag.group(0)):
            assert not re.match(r"^([a-z][a-z0-9+.-]*:|//)", m.group(1)), tag.group(0)
    for m in re.finditer(r"url\(([^)]*)\)", css + page):
        assert not re.match(r"""^['"]?([a-z][a-z0-9+.-]*:|//)""", m.group(1))
    assert "@import" not in css


def test_no_colour_literals_in_sources():
    pat = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl)a?\(|\boklch\(")
    for p in LANDING.rglob("*"):
        rel = p.relative_to(LANDING).parts
        if not p.is_file() or rel[0] in ("captures", "tests", "__pycache__"):
            continue
        assert not pat.search(p.read_text()), p
    assert "rgb" not in "".join(p.read_text() for p in (LANDING / "styles").glob("*.css"))


def test_brand_and_favicons(page):
    for f in ("brand/mark.svg", "brand/wordmark.svg", "brand/wordmark-light.svg",
              "brand/favicon.svg", "brand/favicon.png"):
        assert f"assets/theme/{f}" in page
    assert re.search(r'<link rel="icon"[^>]*favicon\.svg', page)
    assert re.search(r'<link rel="icon"[^>]*favicon\.png', page)
    assert "assets/theme/tokens.css" in page
    assert "var(--rig-" in (LANDING / "styles" / "base.css").read_text()
