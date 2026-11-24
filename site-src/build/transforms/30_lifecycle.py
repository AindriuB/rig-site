"""Insert the `basic` preset's state diagram into workflows.md."""
import json
import re
import sys
from pathlib import Path

_BUILD = str(Path(__file__).resolve().parents[1])
if _BUILD not in sys.path:
    sys.path.insert(0, _BUILD)

from lifecycle import preset_to_mermaid  # noqa: E402

HEADING = "## The `basic` preset"


def apply(ctx) -> None:
    page = ctx.docs_dir / "workflows.md"
    if not page.exists():
        return
    preset_file = ctx.source_dir / "internal/workflow/presets/basic.json"
    if not preset_file.exists():
        raise RuntimeError(f"{ctx.id}: internal/workflow/presets/basic.json is missing")
    lines = page.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if l.rstrip() == HEADING), None)
    if start is None:
        raise RuntimeError(f"{ctx.id}: workflows.md has no '{HEADING}' heading")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"## ", lines[i])),
               len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    fence = preset_to_mermaid(json.loads(preset_file.read_text(encoding="utf-8")))
    if end > 0 and not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"
    lines[end:end] = ["\n", fence]
    page.write_text("".join(lines), encoding="utf-8")
