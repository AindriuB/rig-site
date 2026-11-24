"""Text-level checks on extra.css, one per acceptance item."""
import re
from pathlib import Path

CSS = (Path(__file__).parent.parent / "assets" / "extra.css").read_text()


def rules():
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS)]


def decls(sel_part):
    return [b for s, b in rules() if sel_part in s]


def test_ac1_diagram_cap():
    body = " ".join(decls("#only-light"))
    assert re.search(r"max-width:\s*min\(40rem,\s*100%\)", body)
    assert "height: auto" in body
    assert "text-align: center" in " ".join(b for s, b in rules() if ":has(> img" in s and "#only-light" in s)
    assert "#only-dark" in " ".join(s for s, _ in rules() if "#only-light" in s)


def test_ac2_no_display_on_only_images():
    for s, b in rules():
        if "#only-" in s:
            assert "display" not in b


def test_ac3_hide_first_topic_when_active():
    sels = [(s, b) for s, b in rules() if ".md-header__title--active" in s and ".md-header__topic" in s]
    assert sels
    for s, b in sels:
        assert "visibility: hidden" in b and "pointer-events: none" in b
    joined = " ".join(s for s, _ in sels)
    assert ":first-child" in joined and ":first-child *" in joined


def test_ac4_logo_height_only():
    body = " ".join(s_b[1] for s_b in rules() if ".md-header__button.md-logo img" in s_b[0])
    assert re.search(r"height:\s*1\.4rem", body)
    assert "width: auto" in body
    sel = [s for s, _ in rules() if ".md-header__button.md-logo img" in s][0]
    assert sel.count(".") >= 3  # outranks Material's two-class rule
    drawer = " ".join(b for s, b in rules() if ".md-nav__title .md-nav__button.md-logo img" in s)
    assert re.search(r"height:\s*1\.2rem", drawer) and "width: auto" in drawer


def test_ac5_no_literal_colours():
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", re.sub(r'\[[^\]]*\]', '', CSS))
    assert not re.search(r"\b(rgb|rgba|hsl|hsla)\(", CSS)
