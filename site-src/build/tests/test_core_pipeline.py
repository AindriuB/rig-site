import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import sources
from conftest import FIXTURES, build_fixture_rig

VERSIONS = Path(__file__).resolve().parents[1] / "versions.py"
THEME = FIXTURES / "theme"


def run(rig, tmp, transforms=None, site_repo=None, extra=()):
    site_repo = site_repo or tmp / "site-repo"
    cmd = [sys.executable, str(VERSIONS), "--rig", str(rig), "--site-repo", str(site_repo),
           "--theme", str(THEME), "--build-dir", str(tmp / "build"), *extra]
    if transforms:
        cmd += ["--transforms", str(transforms)]
    else:
        (tmp / "empty").mkdir(exist_ok=True)
        cmd += ["--transforms", str(tmp / "empty")]
    return subprocess.run(cmd, capture_output=True, text=True)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("full")
    rig = build_fixture_rig(tmp / "rig")
    r = run(rig, tmp, FIXTURES / "transforms_ok")
    assert r.returncode == 0, r.stderr + r.stdout
    return tmp


def vdir(built, v):
    return built / "build" / "versions" / v / "build"


def tree(built):
    out = subprocess.run(["git", "-C", str(built / "site-repo"), "ls-tree", "-r",
                          "--name-only", "gh-pages"], capture_output=True, text=True, check=True)
    return out.stdout.split()


def test_core_tag_mapping():
    specs = sources.select_versions(
        ["v0.1.0", "v0.3.0", "v0.3.1", "v0.4.0-rc.1", "v0.10.0", "v0.9.2", "nightly"])
    assert [(s["id"], s["title"], s["aliases"]) for s in specs] == [
        ("0.1", "0.1.0", []), ("0.3", "0.3.1", []), ("0.9", "0.9.2", []),
        ("0.10", "0.10.0", ["latest"]), ("dev", "dev (unreleased)", [])]


def test_core_fixture_deploy_versions(built):
    files = tree(built)
    for v in ("0.1", "0.3", "dev"):
        assert f"docs/{v}/index.html" in files
    assert "docs/0.4/index.html" not in files
    assert "docs/latest/index.html" in files and "docs/index.html" in files
    versions = json.loads(subprocess.run(
        ["git", "-C", str(built / "site-repo"), "show", "gh-pages:docs/versions.json"],
        capture_output=True, text=True, check=True).stdout)
    by_id = {v["version"]: v for v in versions}
    assert by_id["0.3"]["title"] == "0.3.1" and by_id["0.3"]["aliases"] == ["latest"]
    assert by_id["dev"]["title"] == "dev (unreleased)"
    assert not [f for f in files if "/plan/" in f or "phase-" in f]


def test_core_docs_dir_contents(built):
    assert sorted(p.name for p in (vdir(built, "0.3") / "docs").glob("*.md")) == [
        "design.md", "index.md", "release.md", "workflows.md"]
    dev = sorted(p.name for p in (vdir(built, "dev") / "docs").glob("*.md"))
    assert dev == ["alpha.md", "design.md", "index.md", "release.md", "workflows.md", "zeta.md"]
    assert not list((vdir(built, "dev") / "docs").rglob("phase-*")) and \
        not (vdir(built, "dev") / "docs" / "plan").exists() and \
        not (vdir(built, "dev") / "docs" / "sub").exists()


def test_core_links_rewritten_in_pages(built):
    index = (vdir(built, "0.3") / "docs" / "index.md").read_text()
    assert "(workflows.md)" in index and "(design.md#goals)" in index
    assert "https://github.com/AindriuB/rig/blob/v0.3.1/docs/phase-2.md" in index
    dev = (vdir(built, "dev") / "docs" / "alpha.md").read_text()
    assert "https://github.com/AindriuB/rig/blob/main/docs/plan/PLAN.md" in dev


def test_core_generated_config(built):
    cfg = yaml.safe_load((vdir(built, "0.3") / "mkdocs.yml").read_text())
    assert cfg["INHERIT"] == "theme/mkdocs.theme.yml"
    assert cfg["site_name"] == "rig" and cfg["edit_uri"] == "" and cfg["strict"] is True
    assert cfg["site_url"] == "https://aindriub.github.io/rig-site/docs/0.3/"
    assert cfg["repo_url"] == "https://github.com/AindriuB/rig"
    assert cfg["validation"] == {"nav": {"omitted_files": "warn", "not_found": "warn"}}
    assert cfg["plugins"] == ["search"] and cfg["extra"] == {"version": {"provider": "mike"}}
    assert cfg["markdown_extensions"] == [
        "admonition", "pymdownx.details", "pymdownx.superfences", "pymdownx.highlight",
        "pymdownx.inlinehilite", "tables", "attr_list", "md_in_html",
        {"toc": {"permalink": True}}]


def test_core_generated_nav(built):
    cfg = yaml.safe_load((vdir(built, "dev") / "mkdocs.yml").read_text())
    assert cfg["nav"] == [
        {"Overview": "index.md"}, {"The workflow file": "workflows.md"}, {"Design": "design.md"},
        {"Release notes": "release.md"}, {"Alpha": "alpha.md"}, {"Zeta": "zeta.md"}]


def test_core_theme_installed(built):
    assert (vdir(built, "0.1") / "theme" / "mkdocs.theme.yml").is_file()
    assert (vdir(built, "0.1") / "theme" / "overrides" / "main.html").is_file()
    assert (vdir(built, "0.1") / "docs" / "assets" / "theme" / "extra.css").is_file()


def test_core_dev_home_starts_with_unreleased_warning(built):
    dev = (vdir(built, "dev") / "docs" / "index.md").read_text()
    assert dev.startswith('!!! warning "Unreleased"\n') and "rig `main`" in dev.split("\n\n")[0]
    assert not (vdir(built, "0.3") / "docs" / "index.md").read_text().startswith("!!!")


def test_core_transform_runs_and_may_add_assets(built):
    assert (vdir(built, "0.3") / "docs" / "assets" / "mark.txt").read_text() == "0.3"
    assert (vdir(built, "0.3") / "docs" / "index.md").read_text().endswith("Transformed.\n")


def test_core_refuses_rig_site_repo_before_writing(tmp_path):
    root = Path(__file__).resolve().parents[3]
    rig = build_fixture_rig(tmp_path / "rig")
    r = run(rig, tmp_path, site_repo=root)
    assert r.returncode != 0 and "rig-site repository" in r.stderr
    assert not (tmp_path / "build").exists()


def test_core_creates_missing_scratch_repo(tmp_path):
    rig = build_fixture_rig(tmp_path / "rig")
    r = run(rig, tmp_path, site_repo=tmp_path / "deep" / "scratch")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "deep" / "scratch" / ".git").exists()


def test_core_raising_transform_fails_naming_file(tmp_path):
    rig = build_fixture_rig(tmp_path / "rig")
    r = run(rig, tmp_path, FIXTURES / "transforms_raise")
    assert r.returncode != 0 and "10_boom.py" in r.stderr


def test_core_transform_without_apply_fails(tmp_path):
    rig = build_fixture_rig(tmp_path / "rig")
    r = run(rig, tmp_path, FIXTURES / "transforms_noapply")
    assert r.returncode != 0 and "10_nothing.py" in r.stderr and "apply" in r.stderr


def test_core_broken_relative_link_fails_naming_page(tmp_path):
    rig = build_fixture_rig(tmp_path / "rig")
    r = run(rig, tmp_path, FIXTURES / "transforms_badlink")
    assert r.returncode != 0 and "broken.md" in r.stdout + r.stderr
