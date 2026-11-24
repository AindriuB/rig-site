import importlib.util
import json
from pathlib import Path

import pytest

from context import BuildError, VersionContext
from lifecycle import preset_to_mermaid

FIX = Path(__file__).parent / "fixtures" / "lifecycle"
TRANSFORM = Path(__file__).parents[1] / "transforms" / "30_lifecycle.py"
PRESET = json.loads((FIX / "basic.json").read_text())


def _transform():
    spec = importlib.util.spec_from_file_location("t30", TRANSFORM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ctx(tmp_path, preset=True, page=None):
    src, docs = tmp_path / "src", tmp_path / "build" / "docs"
    docs.mkdir(parents=True)
    if preset:
        (src / "internal/workflow/presets").mkdir(parents=True)
        (src / "internal/workflow/presets/basic.json").write_text(json.dumps(PRESET))
    if page is not None:
        (docs / "workflows.md").write_text(page)
    return VersionContext(id="v0.5.0", title="t", ref="v0.5.0", is_dev=False, aliases=[],
                          source_dir=src, build_dir=tmp_path / "build", docs_dir=docs,
                          cache_dir=tmp_path / "cache")


def test_alt_line_names_states_and_routes():
    out = preset_to_mermaid(PRESET).splitlines()
    assert out[0] == "```mermaid" and out[1].startswith("%% alt: ")
    assert out[2] == "stateDiagram-v2"
    for word in ("open", "active", "done", "stopped", "start", "finish", "decide", "reason"):
        assert word in out[1]


def test_edges_and_actions():
    out = preset_to_mermaid(PRESET)
    assert "[*] --> open" in out and "done --> [*]" in out
    assert "open --> stopped : reason" in out and "active --> stopped : reason" in out
    assert "done --> stopped" not in out
    assert "stopped --> open : previous" in out and "stopped --> active : previous" in out
    assert 'state "open (start)" as open' in out


def test_golden():
    assert preset_to_mermaid(PRESET) == (FIX / "basic.golden.md").read_text()


def test_deterministic():
    assert preset_to_mermaid(PRESET) == preset_to_mermaid(json.loads(json.dumps(PRESET)))


def test_inserts_at_end_of_section(tmp_path):
    page = "# W\n\n## The `basic` preset\n\nText.\n\n## The file\n\nMore.\n"
    ctx = _ctx(tmp_path, page=page)
    _transform().apply(ctx)
    text = (ctx.docs_dir / "workflows.md").read_text()
    fence = preset_to_mermaid(PRESET)
    assert text == "# W\n\n## The `basic` preset\n\nText.\n\n" + fence + "\n## The file\n\nMore.\n"


def test_inserts_when_section_is_last(tmp_path):
    ctx = _ctx(tmp_path, page="## The `basic` preset\n\nText.")
    _transform().apply(ctx)
    assert (ctx.docs_dir / "workflows.md").read_text() == (
        "## The `basic` preset\n\nText.\n\n" + preset_to_mermaid(PRESET))


def test_heading_inside_fence_does_not_end_section(tmp_path):
    page = "## The `basic` preset\n\n```sh\n## not a heading\n```\n\n## Next\n"
    ctx = _ctx(tmp_path, page=page)
    _transform().apply(ctx)
    text = (ctx.docs_dir / "workflows.md").read_text()
    assert text == ("## The `basic` preset\n\n```sh\n## not a heading\n```\n\n"
                    + preset_to_mermaid(PRESET) + "\n## Next\n")


def test_no_workflows_page_is_noop(tmp_path):
    ctx = _ctx(tmp_path, preset=False)
    _transform().apply(ctx)
    assert list(ctx.docs_dir.iterdir()) == []


def test_missing_preset_fails_naming_version(tmp_path):
    ctx = _ctx(tmp_path, preset=False, page="## The `basic` preset\n")
    with pytest.raises(Exception, match=r"v0\.5\.0.*basic\.json"):
        _transform().apply(ctx)


def test_missing_heading_fails_naming_version(tmp_path):
    ctx = _ctx(tmp_path, page="# W\n\n## Other\n")
    with pytest.raises(Exception, match=r"v0\.5\.0.*basic. preset"):
        _transform().apply(ctx)
