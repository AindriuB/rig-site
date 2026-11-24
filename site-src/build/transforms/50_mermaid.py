"""Replace every mermaid fence with a light and a dark pre-rendered SVG image."""
import importlib.util
import shutil
import sys
from pathlib import Path

from context import BuildError


def _render_module():
    path = Path(__file__).resolve().parents[1] / "mermaid" / "render.py"
    spec = importlib.util.spec_from_file_location("rig_mermaid_render", path)
    if spec.name in sys.modules:
        return sys.modules[spec.name]
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _esc(alt: str) -> str:
    return alt.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def apply(ctx, runner=None):
    r = _render_module()
    runner = runner or r.run_docker
    out_dir = ctx.docs_dir / "assets" / "diagrams"
    for page in sorted(ctx.docs_dir.rglob("*.md")):
        rel = page.relative_to(ctx.docs_dir)
        text = page.read_text(encoding="utf-8")
        fences = r.find_fences(text)
        if not fences:
            continue
        lines = text.split("\n")
        stem = "-".join([*rel.parent.parts, rel.stem])
        prefix = "../" * len(rel.parent.parts)
        for n, f in reversed(list(enumerate(fences, 1))):
            where = f"{rel.as_posix()}:{f.line}"
            alt = r.alt_text(f.source)
            if alt is None:
                raise BuildError(f"{where}: mermaid fence has no %% alt: line")
            imgs = []
            for scheme in r.SCHEMES:
                svg = r.render_svg(f.source, scheme, ctx.cache_dir, where, runner)
                name = f"{stem}-{n}-{scheme}.svg"
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(svg, out_dir / name)
                imgs.append(f"![{_esc(alt)}]({prefix}assets/diagrams/{name}#only-{scheme})")
            lines[f.start:f.end + 1] = [imgs[0] + imgs[1]]
        page.write_text("\n".join(lines), encoding="utf-8")
