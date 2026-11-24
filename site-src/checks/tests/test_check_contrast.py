"""Tests for check_contrast.py (AC5, AC6)."""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "site-src" / "checks" / "check_contrast.py"
TOKENS = ROOT / "site-src" / "theme" / "assets" / "tokens.css"

spec = importlib.util.spec_from_file_location("check_contrast", SCRIPT)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


def run(css_path: Path | None = None):
    args = [sys.executable, str(SCRIPT)] + ([str(css_path)] if css_path else [])
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def test_real_tokens_pass():
    r = run()
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("\n") == 2 * 13  # one line per pair, both sets


def test_one_failing_pair_fails_and_is_named(tmp_path):
    css = TOKENS.read_text()
    # dark --rig-text-muted -> nearly the dark bg colour
    bad = css.replace("--rig-text-muted: #a4abb6;", "--rig-text-muted: #1a1c20;", 1)
    assert bad != css
    p = tmp_path / "tokens.css"
    p.write_text(bad)
    r = run(p)
    assert r.returncode == 1
    assert "dark: --rig-text-muted on --rig-bg" in r.stderr
    assert "light:" not in r.stderr


@pytest.mark.parametrize("scheme_marker", ['[data-md-color-scheme="default"]', ":root,"])
def test_missing_token_fails_in_either_set(tmp_path, scheme_marker):
    css = TOKENS.read_text()
    start = css.index(scheme_marker)
    end = css.index("}", start)
    block = re.sub(r"\n\s*--rig-link:[^;]*;", "", css[start:end])
    p = tmp_path / "tokens.css"
    p.write_text(css[:start] + block + css[end:])
    r = run(p)
    assert r.returncode == 1
    assert "--rig-link missing" in r.stderr


def test_ratio_known_values():
    assert cc.ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert cc.ratio("#777777", "#777777") == pytest.approx(1.0)


def test_non_text_threshold_is_three():
    css = TOKENS.read_text()
    # light border -> same as bg: ratio 1 fails the 3:1 pair
    bad = css.replace("--rig-border: #858b95;", "--rig-border: #f7f6f3;")
    _, fails = cc.check(bad)
    assert any("light: --rig-border on --rig-bg" in f for f in fails)


def test_media_light_set_must_match_default(tmp_path):
    css = TOKENS.read_text()
    i = css.index("@media")
    bad = css[:i] + css[i:].replace("--rig-text-muted: #4a515b;", "--rig-text-muted: #f0f0f0;")
    assert bad != css
    p = tmp_path / "tokens.css"
    p.write_text(bad)
    r = run(p)
    assert r.returncode == 1
    assert "tokens.css:" in r.stderr and "@media" in r.stderr


def test_unreadable_file_reports_path(tmp_path):
    r = run(tmp_path / "nope.css")
    assert r.returncode == 1
    assert "nope.css:" in r.stderr and "Traceback" not in r.stderr
