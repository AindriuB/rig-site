"""Build the landing page and changelog and commit them to the scratch gh-pages root.

Everything at the root of gh-pages except `docs/` (mike's) is replaced on each run.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_RIG = "https://github.com/AindriuB/rig.git"
BRANCH = "gh-pages"
GIT_ENV = {"GIT_AUTHOR_NAME": "rig-site", "GIT_AUTHOR_EMAIL": "rig-site@localhost",
           "GIT_COMMITTER_NAME": "rig-site", "GIT_COMMITTER_EMAIL": "rig-site@localhost"}


class RootError(Exception):
    pass


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                       env={**os.environ, **GIT_ENV})
    if check and r.returncode:
        sys.stderr.write(r.stderr)
        raise RootError(f"{cwd}: git {args[0]} failed (exit {r.returncode})")
    return r


def apply_root(site_repo: Path, landing: Path, changelog: Path) -> bool:
    """Replace the root of gh-pages (all but docs/) with landing, changelog/ and .nojekyll.

    Returns True when a commit was made.
    """
    site_repo = site_repo.resolve()
    exists = _git(site_repo, "rev-parse", "--verify", "-q", f"refs/heads/{BRANCH}",
                  check=False).returncode == 0
    with tempfile.TemporaryDirectory(prefix="rig-site-root-") as tmp:
        wt = Path(tmp) / "wt"
        if exists:
            _git(site_repo, "worktree", "add", "-q", str(wt), BRANCH)
        else:
            _git(site_repo, "worktree", "add", "-q", "--detach", str(wt))
            _git(wt, "checkout", "-q", "--orphan", BRANCH)
        try:
            for p in wt.iterdir():
                if p.name in (".git", "docs"):
                    continue
                if p.is_dir() and not p.is_symlink():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            shutil.copytree(landing, wt, dirs_exist_ok=True)
            shutil.copytree(changelog, wt / "changelog")
            (wt / ".nojekyll").write_text("")
            _git(wt, "add", "-A")
            if exists and not _git(wt, "status", "--porcelain").stdout.strip():
                return False
            _git(wt, "commit", "-q", "-m", "root: landing page and changelog")
            return True
        finally:
            _git(site_repo, "worktree", "remove", "--force", str(wt), check=False)


def _run(cmd: list[str], what: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise RootError(f"{what} failed (exit {r.returncode})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rig", default=DEFAULT_RIG)
    ap.add_argument("--site-repo", type=Path, default=ROOT / ".build" / "site-repo")
    ap.add_argument("--build-dir", type=Path, default=ROOT / ".build")
    args = ap.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="rig-site-parts-") as tmp:
            landing, changelog = Path(tmp) / "landing", Path(tmp) / "changelog"
            _run([sys.executable, str(ROOT / "site-src/landing/build.py"),
                  "--out", str(landing)], "landing build")
            _run([sys.executable, str(ROOT / "site-src/changelog/build.py"),
                  "--out", str(changelog), "--rig", args.rig,
                  "--build-dir", str(args.build_dir)], "changelog build")
            made = apply_root(args.site_repo, landing, changelog)
            print("root: committed" if made else "root: unchanged", flush=True)
    except RootError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
