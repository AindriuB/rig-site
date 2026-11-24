import re
import sys
from pathlib import Path

import pytest

LANDING = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANDING))
import build  # noqa: E402


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    d = tmp_path_factory.mktemp("v35")
    build.build(d)
    return (d / "index.html").read_text(encoding="utf-8")


def section(page, name):
    return re.search(rf'<section class="slot" id="{name}".*?</section>', page, re.S).group(0)


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_push_panel_accepts_and_refuses(page):
    s = section(page, "push-panel")
    accepted = re.search(r'push-accepted.*?(?=push-refused)', s, re.S).group(0)
    refused = re.search(r'push-refused.*', s, re.S).group(0)
    for t in ("task/", "record/", "task id", "exists locally", "not the default branch"):
        assert t in accepted, t
    for t in ("the default branch", "a tag", "a refspec", "a force push"):
        assert t in refused, t
    assert refused.count("Refused:") == 4  # a text label per item, not colour alone
    assert "✕" in refused


def test_push_panel_refused_treatment_is_not_colour_only():
    css = (LANDING / "styles" / "push-panel.css").read_text()
    assert re.search(r"\.push-refused\s*\{[^}]*dashed", css)
    assert "line-through" in css


def test_forges(page):
    s = section(page, "forges")
    svg = re.search(r"<svg.*?</svg>", s, re.S).group(0)
    for t in (">rig<", ">gh<", ">glab<", ">GitHub<", ">GitLab<", ">Jira<", "OS keychain", "the login you already have"):
        assert t in svg, t
    assert s.count('role="img"') == 1
    assert "keychain" in text_of(s.replace(svg, ""))


def test_state(page):
    s = section(page, "state")
    svg = re.search(r"<svg.*?</svg>", s, re.S).group(0)
    for t in ("refs/rig/", ".git/rig/", "working branches", "not pushed or fetched"):
        assert t in svg, t
    assert "outside any branch" in text_of(s.replace(svg, ""))
    assert "does not push or fetch" in text_of(s.replace(svg, "")) or "do not push or fetch" in text_of(s)


def test_slots_have_styles():
    for n in ("push-panel", "forges", "state"):
        assert (LANDING / "styles" / f"{n}.css").read_text().strip()
