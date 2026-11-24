import pytest


def lines(r):
    return r.stderr.splitlines()


def test_clean_passes(run_site):
    r = run_site("clean")
    assert r.returncode == 0 and r.stderr == ""


def test_docs_version_pages_and_bundle_pass(run_site):
    assert run_site("docs_ok").returncode == 0
    assert run_site("bundle_ok").returncode == 0


def test_font_reference(run_site):
    r = run_site("font_ref")
    assert r.returncode == 1
    assert "page.html: third-party reference 'fonts.googleapis'" in lines(r)


def test_bundle_extra_token(run_site):
    r = run_site("bundle_extra")
    assert r.returncode == 1
    assert any(l.startswith("docs/1.0/assets/javascripts: Material bundle") for l in lines(r))


def test_bundle_missing_token(run_site):
    r = run_site("bundle_missing")
    assert r.returncode == 1
    assert any("not exactly the two expected" in l for l in lines(r))


def test_external_script(run_site):
    r = run_site("ext_script")
    assert r.returncode == 1
    assert "index.html: script src is external: https://cdn.example.com/x.js" in lines(r)
    assert "index.html: script src is external: //cdn.example.com/y.js" in lines(r)


def test_external_stylesheet(run_site):
    r = run_site("ext_css")
    assert r.returncode == 1
    assert "index.html: stylesheet href is external: https://cdn.example.com/x.css" in lines(r)


def test_plan_segment(run_site):
    r = run_site("excl_plan")
    assert r.returncode == 1
    assert "plan: excluded path segment 'plan'" in lines(r)
    assert "docs/1.0/plan: excluded path segment 'plan'" in lines(r)


def test_phase_prefix(run_site):
    r = run_site("excl_phase")
    assert r.returncode == 1
    assert "phase-1: excluded path segment 'phase-1' starts with 'phase-'" in lines(r)


def test_leaked_planning_page(run_site):
    r = run_site("leak_page")
    assert r.returncode == 1
    assert "HISTORY: planning page 'HISTORY' leaked into the site" in lines(r)


@pytest.mark.parametrize("name,msg", [
    ("mermaid_class", 'index.html: contains class="mermaid"'),
    ("mermaid_lang", "index.html: contains language-mermaid"),
    ("mermaid_script", "index.html: script src mentions mermaid: assets/mermaid.js"),
])
def test_mermaid_markers(run_site, name, msg):
    r = run_site(name)
    assert r.returncode == 1
    assert msg in lines(r)


@pytest.mark.parametrize("name", ["img_noalt", "img_emptyalt"])
def test_img_alt(run_site, name):
    r = run_site(name)
    assert r.returncode == 1
    assert "index.html: img without alt: a.png" in lines(r)


def test_tree_unset_or_missing(run_site, tmp_path):
    r = run_site("x", unset=True)
    assert r.returncode == 1 and r.stderr.startswith("RIG_SITE_TREE:")
    r = run_site("x", tree=tmp_path / "nope")
    assert r.returncode == 1 and r.stderr.startswith("RIG_SITE_TREE:")


def test_external_backslash_and_split_scheme(run_site):
    r = run_site("ext_backslash")
    assert r.returncode == 1
    assert len([l for l in lines(r) if "script src is external" in l]) == 3


def test_duplicate_attrs_first_wins(run_site):
    r = run_site("dup_attrs")
    assert r.returncode == 1
    assert "index.html: script src is external: https://cdn.example.com/c.js" in lines(r)
    assert "index.html: img without alt: e.png" in lines(r)


def test_duplicate_href_first_wins(run_site):
    r = run_site("ext_css_dup")
    assert r.returncode == 1
    assert "index.html: stylesheet href is external: https://cdn.example.com/d.css" in lines(r)


def test_planning_files_directly_under_docs(run_site):
    r = run_site("leak_docs_root")
    assert r.returncode == 1
    assert "docs/conventions.md: planning page 'conventions.md' leaked into the site" in lines(r)
    assert "docs/HISTORY.html: planning page 'HISTORY.html' leaked into the site" in lines(r)
    assert "docs/release.md: planning page 'release.md' leaked into the site" in lines(r)


def test_planning_dir_in_version_slot(run_site):
    r = run_site("leak_docs_seg")
    assert r.returncode == 1
    assert "docs/conventions: planning page 'conventions' leaked into the site" in lines(r)
