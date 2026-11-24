from nav import build_nav, page_title


def make(tmp_path, files):
    for n, t in files.items():
        (tmp_path / n).write_text(t)
    return tmp_path


def test_core_nav_order(tmp_path):
    d = make(tmp_path, {n: f"# T {n}\n" for n in
                        ["index.md", "release.md", "zeta.md", "alpha.md", "design.md", "workflows.md"]})
    assert [list(i.values())[0] for i in build_nav(d)] == [
        "index.md", "workflows.md", "design.md", "release.md", "alpha.md", "zeta.md"]
    assert list(build_nav(d)[0]) == ["Overview"]


def test_core_nav_order_skips_absent(tmp_path):
    d = make(tmp_path, {"index.md": "# a\n", "design.md": "# D\n", "b.md": "# B\n"})
    assert [list(i.values())[0] for i in build_nav(d)] == ["index.md", "design.md", "b.md"]


def test_core_nav_title_is_plain_first_heading(tmp_path):
    p = make(tmp_path, {"a.md": "```\n# not me\n```\n\n# The `rig` [file](x.md) **now**\n\n# Second\n"})
    assert page_title(p / "a.md") == "The rig file now"
