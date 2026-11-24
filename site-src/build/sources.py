"""Fetch rig and map its tags and `main` to site versions."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from context import BuildError

_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise BuildError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def fetch_rig(rig: str, mirror: Path) -> None:
    """Create or refresh the bare mirror with every tag and `main`."""
    if not mirror.exists():
        mirror.parent.mkdir(parents=True, exist_ok=True)
        _git("init", "--bare", "-q", str(mirror))
    _git("--git-dir", str(mirror), "fetch", "-q", "--force", "--prune", rig,
         "+refs/tags/*:refs/tags/*", "+refs/heads/main:refs/heads/main")


def select_versions(tags: list[str], has_main: bool = True) -> list[dict]:
    """Return version specs, oldest first, `dev` last."""
    best: dict[tuple[int, int], tuple[int, str]] = {}
    for t in tags:
        m = _TAG.match(t)
        if not m:
            continue
        major, minor, patch = map(int, m.groups())
        if (major, minor) not in best or patch > best[(major, minor)][0]:
            best[(major, minor)] = (patch, t)
    minors = sorted(best)
    specs = []
    for i, key in enumerate(minors):
        patch, tag = best[key]
        specs.append({
            "id": f"{key[0]}.{key[1]}", "title": f"{key[0]}.{key[1]}.{patch}",
            "ref": tag, "git_ref": f"refs/tags/{tag}", "is_dev": False,
            "aliases": ["latest"] if i == len(minors) - 1 else [],
        })
    if has_main:
        specs.append({"id": "dev", "title": "dev (unreleased)", "ref": "main",
                      "git_ref": "refs/heads/main", "is_dev": True, "aliases": []})
    return specs


def list_versions(mirror: Path) -> list[dict]:
    tags = _git("--git-dir", str(mirror), "tag", "--list").split()
    main = _git("--git-dir", str(mirror), "rev-parse", "--verify", "-q",
                "refs/heads/main", check=False).strip()
    return select_versions(tags, has_main=bool(main))


def export_tree(mirror: Path, git_ref: str, dest: Path) -> None:
    dest.mkdir(parents=True)
    arc = subprocess.run(["git", "--git-dir", str(mirror), "archive", git_ref],
                         capture_output=True)
    if arc.returncode:
        raise BuildError(f"git archive {git_ref}: {arc.stderr.decode().strip()}")
    r = subprocess.run(["tar", "-x", "-C", str(dest)], input=arc.stdout,
                       capture_output=True)
    if r.returncode:
        raise BuildError(f"tar: {r.stderr.decode().strip()}")
