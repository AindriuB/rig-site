import pytest

from context import BuildError
from links import rewrite_links

PUB = {"README.md": "index.md", "docs/design.md": "design.md", "docs/workflows.md": "workflows.md"}
BLOB = "https://x/blob/v1/"


def rw(text, src="README.md"):
    return rewrite_links(text, src, PUB, BLOB)


def test_core_published_link_becomes_page_with_anchor():
    assert rw("[d](docs/design.md#goals)") == "[d](design.md#goals)"


def test_core_link_between_docs_pages_and_to_readme():
    assert rw("[r](../README.md) [w](workflows.md)", "docs/design.md") == "[r](index.md) [w](workflows.md)"


def test_core_unpublished_link_becomes_blob_with_anchor():
    assert rw("[p](docs/phase-2.md#scope) [l](LICENSE)") == (
        f"[p]({BLOB}docs/phase-2.md#scope) [l]({BLOB}LICENSE)")
    assert rw("[p](phase-2.md#s)", "docs/design.md") == f"[p]({BLOB}docs/phase-2.md#s)"


def test_core_absolute_anchor_and_mailto_untouched():
    text = "[a](https://e.com/x.md) [b](#top) [c](mailto:a@b.c) <https://e.com>"
    assert rw(text) == text


def test_core_code_spans_and_fences_untouched():
    text = "`[a](docs/design.md)`\n\n```md\n[a](docs/design.md)\n```\n\n~~~\n[a](LICENSE)\n~~~\n"
    assert rw(text) == text


def test_core_link_text_with_code_span_is_rewritten():
    assert rw("[`design`](docs/design.md)") == "[`design`](design.md)"


def test_core_reference_style_links():
    assert rw("[d][1]\n\n[1]: docs/design.md#x \"T\"\n[2]: LICENSE") == (
        f"[d][1]\n\n[1]: design.md#x \"T\"\n[2]: {BLOB}LICENSE")


def test_core_nested_badge_link_rewrites_outer_only():
    text = "[![b](https://img/x.svg)](docs/design.md)"
    assert rw(text) == "[![b](https://img/x.svg)](design.md)"


def test_core_relative_image_fails_with_path_and_line():
    with pytest.raises(BuildError, match=r"README\.md:3: relative image"):
        rw("a\n\n![alt](docs/pic.png)\n")


def test_core_relative_reference_image_fails():
    with pytest.raises(BuildError, match=r"README\.md:3: relative image"):
        rw("![alt][p]\n\n[p]: docs/pic.png\n")
