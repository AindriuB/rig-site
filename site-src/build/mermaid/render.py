"""Offline Mermaid rendering: fence scanning, the pinned docker call and the SVG cache."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from context import BuildError

HERE = Path(__file__).resolve().parent
IMAGE = ("minlag/mermaid-cli:10.9.1@sha256:"
         "f0e8d29ef5385d797724d78c2a1bb00c8398476e8370f0219c0da86cce07d44c")
SCHEMES = ("light", "dark")
ALT_RE = re.compile(r"^%%\s*alt:\s*(\S.*?)\s*$")
OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*([^\s`]*)")


@dataclass
class Fence:
    start: int  # 0-based index of the opening line
    end: int  # 0-based index of the closing line (inclusive)
    line: int  # 1-based line number of the opening line
    source: str


def find_fences(text: str) -> list[Fence]:
    """Top-level ```mermaid fences. Fences nested in another fence are not seen."""
    lines = text.split("\n")
    out: list[Fence] = []
    i = 0
    while i < len(lines):
        m = OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        marker, lang = m.group(1), m.group(2)
        close = re.compile(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$")
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            j += 1
        if lang == "mermaid" and j < len(lines):
            out.append(Fence(i, j, i + 1, "\n".join(lines[i + 1:j])))
        i = j + 1
    return out


def alt_text(source: str) -> str | None:
    for line in source.split("\n"):
        if line.strip():
            m = ALT_RE.match(line.strip())
            return m.group(1) if m else None
    return None


def config_path(scheme: str) -> Path:
    return HERE / f"config-{scheme}.json"


def cache_key(source: str, scheme: str) -> str:
    h = hashlib.sha256()
    for part in (source.encode(), config_path(scheme).read_bytes(), IMAGE.encode()):
        h.update(hashlib.sha256(part).digest())
    return h.hexdigest()


def docker_argv(indir: Path, outdir: Path) -> list[str]:
    return ["docker", "run", "--rm", "--network", "none", "-u", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{indir}:/in:ro", "-v", f"{outdir}:/out", IMAGE,
            "-i", "/in/diagram.mmd", "-o", "/out/diagram.svg", "-c", "/in/config.json",
            "-b", "transparent"]


def run_docker(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def render_svg(source: str, scheme: str, cache_dir: Path, where: str, runner=run_docker) -> Path:
    """Return the cached SVG for `source`, rendering it first on a miss. `where` is `page:line`."""
    cache = cache_dir / "mermaid"
    cache.mkdir(parents=True, exist_ok=True)
    hit = cache / f"{cache_key(source, scheme)}.svg"
    if hit.exists():
        return hit
    with tempfile.TemporaryDirectory(prefix="rig-mermaid-") as tmp:
        indir, outdir = Path(tmp) / "in", Path(tmp) / "out"
        indir.mkdir()
        outdir.mkdir()
        (indir / "diagram.mmd").write_text(source, encoding="utf-8")
        shutil.copyfile(config_path(scheme), indir / "config.json")
        for d in (indir, outdir):
            d.chmod(0o777)
        (indir / "diagram.mmd").chmod(0o644)
        proc = runner(docker_argv(indir, outdir))
        svg = outdir / "diagram.svg"
        if proc.returncode != 0 or not svg.exists():
            raise BuildError(f"{where}: mermaid render failed ({scheme}): {proc.stderr.strip()}")
        part = hit.with_suffix(".tmp")
        shutil.copyfile(svg, part)
        part.replace(hit)
    return hit
