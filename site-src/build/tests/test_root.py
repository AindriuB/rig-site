import os
import shutil
import subprocess
from pathlib import Path

import pytest

import root
from conftest import ENV

FIX = Path(__file__).parent / "fixtures" / "root"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env={**os.environ, **ENV}).stdout


@pytest.fixture
def site(tmp_path):
    """A scratch repo whose gh-pages holds mike's docs/ and stale root files."""
    repo = tmp_path / "site"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "scratch")
    git(repo, "commit", "-q", "--allow-empty", "-m", "scratch")
    git(repo, "checkout", "-q", "--orphan", "gh-pages")
    for name, text in {"docs/0.5/index.html": "v", "docs/versions.json": "[]",
                       "old.html": "stale", "gone/deep.txt": "stale", "index.html": "old"}.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "mike")
    git(repo, "checkout", "-q", "scratch")
    return repo


def tree(repo):
    return sorted(git(repo, "ls-tree", "-r", "--name-only", "gh-pages").split())


def test_root_replaced_and_stale_removed(site):
    assert root.apply_root(site, FIX / "landing", FIX / "changelog")
    files = tree(site)
    assert "old.html" not in files and "gone/deep.txt" not in files
    assert {"index.html", "assets/a.css", "changelog/index.html", ".nojekyll"} <= set(files)
    assert git(site, "show", "gh-pages:index.html").strip() == "<h1>new landing</h1>"


def test_docs_untouched(site):
    before = git(site, "rev-parse", "gh-pages:docs").strip()
    root.apply_root(site, FIX / "landing", FIX / "changelog")
    assert git(site, "rev-parse", "gh-pages:docs").strip() == before


def test_second_run_is_noop_and_updates_replace(site, tmp_path):
    root.apply_root(site, FIX / "landing", FIX / "changelog")
    head = git(site, "rev-parse", "gh-pages")
    assert not root.apply_root(site, FIX / "landing", FIX / "changelog")
    assert git(site, "rev-parse", "gh-pages") == head
    land = tmp_path / "land2"
    shutil.copytree(FIX / "landing", land)
    (land / "assets" / "a.css").unlink()
    assert root.apply_root(site, land, FIX / "changelog")
    assert "assets/a.css" not in tree(site)
    assert git(site, "rev-parse", "gh-pages:docs").strip()


def test_creates_branch_when_missing(tmp_path):
    repo = tmp_path / "s"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "scratch")
    git(repo, "commit", "-q", "--allow-empty", "-m", "scratch")
    assert root.apply_root(repo, FIX / "landing", FIX / "changelog")
    assert "index.html" in tree(repo)
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "scratch"
