"""Motion bounds for the hero pulse and the forges note class."""
import re
from pathlib import Path

STYLES = Path(__file__).resolve().parent.parent / "styles"
PARTIALS = Path(__file__).resolve().parent.parent / "partials"
HERO = (STYLES / "hero.css").read_text()
FORGES = (STYLES / "forges.css").read_text()


def _pulse_rule():
    m = re.search(r"\.ci-pulse\s*\{\s*animation:\s*([^;]+);", HERO)
    assert m, "no .ci-pulse animation"
    return m.group(1)


def _outside_motion_block(css):
    i = css.index("@media (prefers-reduced-motion: no-preference)")
    return css[:i]


def test_pulse_is_finite_and_within_card_length():
    assert "infinite" not in HERO
    parts = _pulse_rule().split()
    dur = float(next(p for p in parts if p.endswith("s") and p[:-1].replace(".", "").isdigit())[:-1])
    n = int(next(p for p in parts if p.isdigit()))
    assert n >= 1 and n * dur <= 12


def test_pulse_rests_invisible_after_last_iteration():
    assert "forwards" in _pulse_rule().split()
    m = re.search(r"@keyframes rig-ci-pulse\s*\{.*?100%\s*\{([^}]*)\}", HERO, re.S)
    assert m and re.search(r"opacity:\s*0\s*;", m.group(1))


def test_all_motion_inside_no_preference_block():
    outside = _outside_motion_block(HERO)
    assert not re.search(r"\b(animation|transition)\b", outside)


def test_centred_note_has_own_class_and_no_x_selector():
    assert "[x=" not in FORGES
    assert re.search(r"\.note-centre\s*\{[^}]*text-anchor:\s*middle", FORGES)
    html = (PARTIALS / "forges.html").read_text()
    assert re.search(r'<text class="[^"]*\bnote-centre\b[^"]*"[^>]*>direct, no gh or glab', html)
