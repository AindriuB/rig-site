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


EXTERNAL = re.compile(r"^\s*([a-z][a-z0-9+.-]*:|//)", re.I)
IMPORT = re.compile(r"@import", re.I)


def _external_refs(page):
    """Every URL-bearing attribute outside <a>, in any quoting."""
    for tag in re.finditer(r"<([a-zA-Z][\w:-]*)\b([^>]*)>", page):
        name, attrs = tag.group(1).lower(), tag.group(2)
        if name == "a":
            continue
        for m in re.finditer(
            r"""\b(src|href|xlink:href|data|poster|srcset|action|formaction)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
            attrs, re.I,
        ):
            value = m.group(2) or m.group(3) or m.group(4) or ""
            if m.group(1).lower() == "srcset":
                # every comma-separated candidate: "<url> [descriptor]"
                for cand in value.split(","):
                    parts = cand.split()
                    yield tag.group(0), parts[0] if parts else ""
            else:
                yield tag.group(0), value


def test_nothing_external_loaded(page, css):
    for tag, url in _external_refs(page):
        assert not EXTERNAL.match(url), tag
    for m in re.finditer(r"url\(([^)]*)\)", css + page):
        assert not re.match(r"""^\s*['"]?\s*([a-z][a-z0-9+.-]*:|//)""", m.group(1), re.I)
    styles = css + "".join(re.findall(r"<style\b[^>]*>(.*?)</style>", page, re.S | re.I))
    assert not IMPORT.search(styles)


def test_external_guard_catches_bad_refs():
    bad = ["<img src='https://example.com/x.png'>", '<embed src="https://example.com/y.svg">',
           '<object data="//example.com/o"></object>', '<image href="http://e.com/i.png"/>',
           "<use xlink:href=https://e.com/s.svg#a />"]
    for b in bad:
        assert any(EXTERNAL.match(u) for _, u in _external_refs(b)), b
    assert any(EXTERNAL.match(u) for _, u in _external_refs('<img srcset="a.png 1x, https://e.com/b.png 2x">'))
    assert not any(EXTERNAL.match(u) for _, u in _external_refs('<img srcset="a.png 1x, b.png 2x">'))
    assert IMPORT.search("@IMPORT url(x.css);")
    assert not list(_external_refs('<a href="https://github.com/x">x</a>'))


COLOUR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl|hwb|lab|lch|oklab|oklch|color|color-mix|light-dark)a?\(",
    re.I,
)
NAMED = re.compile(
    r"(?<![\w-])(?:%s)(?![\w-])" % "|".join([
        "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black",
        "blanchedalmond", "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse",
        "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
        "darkgoldenrod", "darkgray", "darkgrey", "darkgreen", "darkkhaki", "darkmagenta",
        "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen",
        "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise", "darkviolet", "deeppink",
        "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite", "forestgreen",
        "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "grey", "green",
        "greenyellow", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender",
        "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
        "lightgoldenrodyellow", "lightgray", "lightgrey", "lightgreen", "lightpink", "lightsalmon",
        "lightseagreen", "lightskyblue", "lightslategray", "lightslategrey", "lightsteelblue",
        "lightyellow", "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine",
        "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue",
        "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue", "mintcream",
        "mistyrose", "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange",
        "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise", "palevioletred",
        "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "rebeccapurple",
        "red", "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell",
        "sienna", "silver", "skyblue", "slateblue", "slategray", "slategrey", "snow", "springgreen",
        "steelblue", "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat", "white",
        "whitesmoke", "yellow", "yellowgreen"]),
    re.I,
)
# fill/stroke/colour values anywhere (CSS declarations or SVG attributes) must be a
# token reference or a keyword that names no colour.
PAINT_OK = {"none", "currentcolor", "transparent", "inherit", "context-fill", "context-stroke"}
PAINT_CSS = re.compile(
    r"(?<![\w-])(?:fill|stroke|color|background(?:-color)?|border(?:-[a-z]+)*-color|outline-color|stop-color|flood-color)\s*:\s*([^;}]+)", re.I)
PAINT_ATTR = re.compile(r"""\b(?:fill|stroke|color|stop-color|flood-color)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)


STYLE_ATTR = re.compile(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))""", re.I)


def _named_in_style_attrs(text):
    """Named colours in the values of inline style attributes, whatever the property."""
    for m in STYLE_ATTR.finditer(text):
        for decl in (m.group(1) or m.group(2) or m.group(3) or "").split(";"):
            value = decl.partition(":")[2]
            if NAMED.search(value):
                yield decl.strip()


def _bad_paint(value):
    v = value.strip().lower()
    return not (v.startswith("var(--rig-") or v in PAINT_OK or v.startswith("url(#"))


def test_no_colour_literals_in_sources():
    """No colour literal outside the token files: hex/functional colours anywhere, named
    colours in CSS and in inline style attributes, and bad fill/stroke/colour values.

    Exempt: captures/ (verbatim terminal output) and tests/ (this guard's own fixtures).
    """
    for p in LANDING.rglob("*"):
        rel = p.relative_to(LANDING).parts
        if not p.is_file() or rel[0] in ("captures", "tests", "__pycache__"):
            continue
        text = p.read_text()
        assert not COLOUR.search(text), p
        if p.suffix == ".css":
            for m in re.finditer(r"(?<![\w-])[a-z-]+\s*:\s*([^;}{]+)", text):
                assert not NAMED.search(m.group(1)), (p, m.group(0))
        for m in PAINT_CSS.finditer(text):
            assert not _bad_paint(m.group(1)), (p, m.group(0))
        if p.suffix in (".html", ".svg"):
            for m in PAINT_ATTR.finditer(text):
                assert not _bad_paint(m.group(1) or m.group(2)), (p, m.group(0))
            assert not list(_named_in_style_attrs(text)), p


def test_colour_guard_catches_bad_values():
    for bad in (".b{color:white;background:black}", "<rect fill='red'>", "a{color:hwb(0 0% 0%)}",
                "a{x:lab(1 1 1)}", "a{x:color(srgb 1 1 1)}", ".a{stroke:#fff}", '<path fill="blue"/>'):
        hit = COLOUR.search(bad) or NAMED.search(bad) or any(_bad_paint(m.group(1)) for m in PAINT_CSS.finditer(bad)) \
            or any(_bad_paint(m.group(1) or m.group(2)) for m in PAINT_ATTR.finditer(bad))
        assert hit, bad


def test_colour_guard_catches_named_in_style_attrs():
    for bad in ('<p style="color: red">', '<svg style="border-top: 1px solid red"/>',
                "<p style='margin:0;outline:2px dotted blue'>", "<p style=border:red>",
                "<p style=box-shadow:0/0/red>"):
        assert list(_named_in_style_attrs(bad)), bad
    assert not list(_named_in_style_attrs('<p style="color: var(--rig-fg); margin: 0">'))


def test_errors_name_the_file(tmp_path):
    src = make_src(tmp_path, "<p>x</p>\n<!-- include: nope -->", {})
    with pytest.raises(build.BuildError, match=r"index\.html:2: include 'nope'"):
        build.build(tmp_path / "o", src)
    src = make_src(tmp_path / "b", "<p>x</p>", {"extra": "<p>y</p>"})
    with pytest.raises(build.BuildError, match=r"extra\.html"):
        build.build(tmp_path / "o", src)
    src = make_src(tmp_path / "c", "<p>x</p>\n{{capture:zip}}", {})
    with pytest.raises(build.BuildError, match=r"index\.html:2: capture 'zip'"):
        build.build(tmp_path / "o", src)
    src = make_src(tmp_path / "d", "<p>x</p>", {})
    (src / "landing.js").unlink()
    with pytest.raises(build.BuildError, match=r"landing\.js"):
        build.build(tmp_path / "o", src)
    src = make_src(tmp_path / "e", "<p>x</p>", {})
    (src / "styles" / "base.css").unlink()
    with pytest.raises(build.BuildError, match=r"base\.css"):
        build.build(tmp_path / "o", src)


def test_brand_and_favicons(page):
    for f in ("brand/mark.svg", "brand/wordmark.svg", "brand/wordmark-light.svg",
              "brand/favicon.svg", "brand/favicon.png"):
        assert f"assets/theme/{f}" in page
    assert re.search(r'<link rel="icon"[^>]*favicon\.svg', page)
    assert re.search(r'<link rel="icon"[^>]*favicon\.png', page)
    assert "assets/theme/tokens.css" in page
    assert "var(--rig-" in (LANDING / "styles" / "base.css").read_text()


def test_duplicate_capture_names_raise(tmp_path):
    src = make_src(tmp_path, "<p>x</p>", {})
    (src / "captures").mkdir(exist_ok=True)
    (src / "captures" / "01-push.txt").write_text("a")
    (src / "captures" / "04-push.txt").write_text("b")
    with pytest.raises(build.BuildError, match=r"04-push\.txt.*01-push\.txt"):
        build.load_captures(src)
