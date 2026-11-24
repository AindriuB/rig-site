import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

CL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CL))
import build  # noqa: E402

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}

CHANGELOG = """# Changelog

## [Unreleased]

## [0.3.0] - 2026-11-01

- See [the design](docs/design.md) and the [licence](LICENSE).

[Unreleased]: https://github.com/AindriuB/rig/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/AindriuB/rig/compare/v0.2.0...v0.3.0
"""


def make_rig(path: Path, changelog: str | None) -> Path:
    path.mkdir()
    files = {"README.md": "# rig\n", "docs/design.md": "# Design\n"}
    if changelog is not None:
        files["CHANGELOG.md"] = changelog
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "x"]):
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True,
                       env={**os.environ, **ENV})
    return path


def run(rig: Path, tmp: Path):
    out = tmp / "out"
    r = subprocess.run([sys.executable, str(CL / "build.py"), "--out", str(out),
                        "--rig", str(rig), "--build-dir", str(tmp / "work")],
                       capture_output=True, text=True)
    return r, out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cl")
    r, out = run(make_rig(tmp / "rig", CHANGELOG), tmp)
    assert r.returncode == 0, r.stdout + r.stderr
    return tmp, out


def test_builds_index(built):
    _, out = built
    html = (out / "index.html").read_text()
    assert "0.3.0" in html and "2026-11-01" in html


def test_config(built):
    tmp, _ = built
    cfg = yaml.safe_load((tmp / "work" / "changelog" / "mkdocs.yml").read_text())
    assert cfg["INHERIT"] == "theme/mkdocs.theme.yml"
    assert cfg["site_url"] == "https://aindriub.github.io/rig-site/changelog/"
    assert cfg["strict"] is True
    assert cfg["plugins"] == ["search"]
    assert "version" not in cfg.get("extra", {})
    assert cfg["nav"] == [{"Changelog": "index.md"}]


def test_links_rewritten(built):
    _, out = built
    html = (out / "index.html").read_text()
    assert "https://github.com/AindriuB/rig/blob/main/docs/design.md" in html
    assert "https://github.com/AindriuB/rig/blob/main/LICENSE" in html
    assert "https://github.com/AindriuB/rig/compare/v0.2.0...v0.3.0" in html


def test_back_links(built):
    _, out = built
    html = (out / "index.html").read_text()
    assert 'href="../"' in html and 'href="../docs/"' in html


def test_missing_changelog_warns_and_builds(tmp_path):
    r, out = run(make_rig(tmp_path / "rig", None), tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "::warning::" in r.stdout
    html = (out / "index.html").read_text()
    assert "not yet published" in html
    assert "https://github.com/AindriuB/rig/releases" in html


def test_other_error_fails(tmp_path):
    r, _ = run(tmp_path / "nonexistent", tmp_path)
    assert r.returncode == 1
