import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from context import BuildError, VersionContext

BUILD = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "mermaid" / "sample.md"
TOKENS = BUILD.parents[0] / "theme" / "assets" / "tokens.css"


def load(path):
    spec = importlib.util.spec_from_file_location("m_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


transform = load(BUILD / "transforms" / "50_mermaid.py")
render = transform._render_module()

SVG = '<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>'


def make_ctx(tmp_path, pages, vid="v1"):
    docs = tmp_path / vid / "docs"
    docs.mkdir(parents=True)
    for name, text in pages.items():
        (docs / name).parent.mkdir(parents=True, exist_ok=True)
        (docs / name).write_text(text)
    return VersionContext(id=vid, title=vid, ref=vid, is_dev=False, aliases=[],
                          source_dir=tmp_path, build_dir=tmp_path / vid, docs_dir=docs,
                          cache_dir=tmp_path / "cache")


class Stub:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def __call__(self, argv):
        self.calls.append(argv)
        if self.fail:
            return subprocess.CompletedProcess(argv, 1, "", self.fail)
        out = next(a.split(":")[0] for a in argv if a.endswith(":/out"))
        Path(out, "diagram.svg").write_text(SVG)
        return subprocess.CompletedProcess(argv, 0, "", "")


def fence(body, lang="mermaid"):
    return f"```{lang}\n{body}\n```"


def test_mermaid_replaces_fences_numbered_per_page(tmp_path):
    page = "# T\n\n" + fence("%% alt: One.\nflowchart LR\n a-->b") + "\n\ntext\n\n" + \
        fence("%% alt: Two.\nflowchart LR\n c-->d") + "\n"
    ctx = make_ctx(tmp_path, {"a.md": page, "b.md": fence("%% alt: Other.\nflowchart LR\n e-->f")})
    transform.apply(ctx, Stub())
    a = (ctx.docs_dir / "a.md").read_text()
    assert ("![One.](assets/diagrams/a-1-light.svg#only-light)"
            "![One.](assets/diagrams/a-1-dark.svg#only-dark)") in a
    assert "![Two.](assets/diagrams/a-2-light.svg#only-light)" in a
    assert "```" not in a and "text" in a
    assert "![Other.](assets/diagrams/b-1-light.svg#only-light)" in (ctx.docs_dir / "b.md").read_text()
    assert (ctx.docs_dir / "assets/diagrams/a-2-dark.svg").read_text() == SVG


def test_mermaid_leaves_nested_and_other_fences(tmp_path):
    page = ("````markdown\n" + fence("%% alt: x.\nflowchart LR") + "\n````\n\n"
            + fence("print(1)", "python") + "\n\n~~~text\n```mermaid\nx\n```\n~~~\n")
    ctx = make_ctx(tmp_path, {"a.md": page})
    stub = Stub()
    transform.apply(ctx, stub)
    assert (ctx.docs_dir / "a.md").read_text() == page
    assert stub.calls == []


def test_mermaid_nested_page_links_relative(tmp_path):
    ctx = make_ctx(tmp_path, {"sub/p.md": fence("%% alt: Deep.\nflowchart LR")})
    transform.apply(ctx, Stub())
    assert "(../assets/diagrams/sub-p-1-light.svg#only-light)" in (ctx.docs_dir / "sub/p.md").read_text()


def test_mermaid_missing_alt_fails(tmp_path):
    ctx = make_ctx(tmp_path, {"a.md": "# T\n\n" + fence("flowchart LR\n a-->b")})
    with pytest.raises(BuildError, match=r"a\.md:3: mermaid fence has no %% alt: line"):
        transform.apply(ctx, Stub())


def test_mermaid_alt_must_be_first_nonblank_line(tmp_path):
    ctx = make_ctx(tmp_path, {"a.md": fence("\n%% alt: Ok.\nflowchart LR")})
    transform.apply(ctx, Stub())
    ctx2 = make_ctx(tmp_path, {"a.md": fence("flowchart LR\n%% alt: Late.")}, "v2")
    with pytest.raises(BuildError):
        transform.apply(ctx2, Stub())


def test_mermaid_render_error_reports_page_line_stderr(tmp_path):
    ctx = make_ctx(tmp_path, {"a.md": "x\n\n\n" + fence("%% alt: A.\nbogus")})
    with pytest.raises(BuildError) as e:
        transform.apply(ctx, Stub(fail="Parse error on line 2"))
    msg = str(e.value)
    assert "a.md:4" in msg and "Parse error on line 2" in msg


def test_mermaid_cache_reused_across_versions(tmp_path):
    page = fence("%% alt: A.\nflowchart LR\n a-->b")
    stub = Stub()
    transform.apply(make_ctx(tmp_path, {"a.md": page}, "v1"), stub)
    assert len(stub.calls) == 2  # light and dark
    v2 = make_ctx(tmp_path, {"a.md": page}, "v2")
    transform.apply(v2, stub)
    assert len(stub.calls) == 2
    assert (v2.docs_dir / "assets/diagrams/a-1-light.svg").read_text() == SVG
    transform.apply(make_ctx(tmp_path, {"a.md": page.replace("a-->b", "a-->c")}, "v3"), stub)
    assert len(stub.calls) == 4


def test_mermaid_cache_key_covers_config_and_pin(tmp_path, monkeypatch):
    k = render.cache_key("src", "light")
    assert k != render.cache_key("src", "dark")
    monkeypatch.setattr(render, "IMAGE", "other:1")
    assert render.cache_key("src", "light") != k


def test_mermaid_docker_argv(tmp_path):
    argv = render.docker_argv(tmp_path / "i", tmp_path / "o")
    assert argv[:6] == ["docker", "run", "--rm", "--network", "none", "-u"]
    assert render.IMAGE in argv and "@sha256:" in render.IMAGE
    assert argv[argv.index("-b") + 1] == "transparent"
    assert sum(a == "-v" for a in argv) == 2


def _tokens():
    css = TOKENS.read_text()
    dark = css.split("/* Light set")[0]
    light = css.split("/* Light set")[1].split("/* No Material")[0]
    pick = lambda s: set(re.findall(r"#[0-9a-fA-F]{3,8}\b", s))
    return pick(light), pick(dark)


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_mermaid_config_colours_from_tokens(scheme):
    cfg = json.loads(render.config_path(scheme).read_text())
    assert cfg["theme"] == "base" and cfg["flowchart"]["htmlLabels"] is False
    light, dark = _tokens()
    allowed = light if scheme == "light" else dark
    found = set(re.findall(r"#[0-9a-fA-F]{3,8}\b", render.config_path(scheme).read_text()))
    assert found and found <= allowed


@pytest.mark.docker
@pytest.mark.skipif(shutil.which("docker") is None, reason="no docker")
def test_mermaid_docker_end_to_end(tmp_path):
    ctx = make_ctx(tmp_path, {"sample.md": FIXTURE.read_text()})
    transform.apply(ctx)
    text = (ctx.docs_dir / "sample.md").read_text()
    for n in (1, 2):
        for s in ("light", "dark"):
            assert f"(assets/diagrams/sample-{n}-{s}.svg#only-{s})" in text
    assert "```" not in text
    svgs = sorted((ctx.docs_dir / "assets/diagrams").glob("*.svg"))
    assert len(svgs) == 4
    for svg in svgs:
        s = svg.read_text()
        assert "<foreignObject" not in s and "<script" not in s
        urls = re.findall(r"https?://[^\s\"')<]+", s)
        assert all(u.rstrip("/") in ("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink")
                   for u in urls), urls
