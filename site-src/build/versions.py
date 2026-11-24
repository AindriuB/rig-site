"""Build every rig version's docs and deploy each with mike into a scratch repo."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import assemble  # noqa: E402
import sources  # noqa: E402
from context import BuildError, VersionContext  # noqa: E402
from nav import build_nav  # noqa: E402

ROOT = HERE.parents[1]
DEFAULT_RIG = "https://github.com/AindriuB/rig.git"
GIT_ENV = {"GIT_AUTHOR_NAME": "rig-site", "GIT_AUTHOR_EMAIL": "rig-site@localhost",
           "GIT_COMMITTER_NAME": "rig-site", "GIT_COMMITTER_EMAIL": "rig-site@localhost"}


def _git_out(path: Path, *args: str) -> str | None:
    r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def check_site_repo(site_repo: Path) -> None:
    """Refuse the rig-site repository itself, before anything is written."""
    site_repo = site_repo.resolve()
    ours = _git_out(ROOT, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if site_repo.exists():
        if not site_repo.is_dir():
            raise BuildError(f"{site_repo}: --site-repo is not a directory")
        top = _git_out(site_repo, "rev-parse", "--show-toplevel")
        if top is not None and Path(top).resolve() == site_repo:
            theirs = _git_out(site_repo, "rev-parse", "--path-format=absolute",
                              "--git-common-dir")
            if ours and theirs and Path(theirs).resolve() == Path(ours).resolve():
                raise BuildError(f"{site_repo}: --site-repo is the rig-site repository "
                                 "or shares its git dir")
        elif any(site_repo.iterdir()):
            raise BuildError(f"{site_repo}: --site-repo exists and is not a git repository")
    elif ours and site_repo == Path(ours).resolve().parent:
        raise BuildError(f"{site_repo}: --site-repo is the rig-site repository")


def ensure_site_repo(site_repo: Path) -> None:
    if not (site_repo / ".git").exists():
        site_repo.mkdir(parents=True, exist_ok=True)
        _run(["git", "init", "-q", str(site_repo)], site_repo, "git init", str(site_repo))
    # mike reads HEAD's commit, so the scratch repo needs one.
    if _git_out(site_repo, "rev-parse", "--verify", "-q", "HEAD") is None:
        _run(["git", "commit", "-q", "--allow-empty", "-m", "scratch"], site_repo,
             "git commit")


def _run(cmd: list[str], cwd: Path, what: str, where: str | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, **GIT_ENV,
                            "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"})
    if r.returncode:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise BuildError(f"{where or cwd}: {what} failed (exit {r.returncode})")


def _mike(*args: str) -> list[str]:
    return [sys.executable, "-c", "from mike.driver import main; main()", *args]


def build_version(spec: dict, mirror: Path, work: Path, cache: Path, theme: Path,
                  transforms: Path, site_repo: Path) -> Path:
    vdir = work / "versions" / spec["id"]
    if vdir.exists():
        shutil.rmtree(vdir)
    ctx = VersionContext(
        id=spec["id"], title=spec["title"], ref=spec["ref"], is_dev=spec["is_dev"],
        aliases=list(spec["aliases"]), source_dir=vdir / "src", build_dir=vdir / "build",
        docs_dir=vdir / "build" / "docs", cache_dir=cache)
    sources.export_tree(mirror, spec["git_ref"], ctx.source_dir)
    ctx.build_dir.mkdir(parents=True)
    assemble.assemble_pages(ctx)
    assemble.install_theme(ctx.build_dir, ctx.docs_dir, theme)
    assemble.run_transforms(ctx, transforms)
    if ctx.is_dev:
        assemble.add_dev_notice(ctx)
    config = assemble.write_config(ctx, build_nav(ctx.docs_dir))
    print(f"deploying {ctx.id} ({ctx.title})", flush=True)
    _run(_mike("deploy", "--deploy-prefix", "docs", "--update-aliases",
               "--alias-type", "redirect", "-F", str(config), "-t", ctx.title,
               ctx.id, *ctx.aliases), site_repo, f"mike deploy {ctx.id}", str(config))
    return config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rig", default=DEFAULT_RIG)
    ap.add_argument("--site-repo", type=Path, default=ROOT / ".build" / "site-repo")
    ap.add_argument("--theme", type=Path, default=ROOT / "site-src" / "theme")
    ap.add_argument("--transforms", type=Path, default=HERE / "transforms")
    ap.add_argument("--build-dir", type=Path, default=ROOT / ".build",
                    help="scratch area for the rig mirror and per-version builds")
    args = ap.parse_args(argv)
    try:
        check_site_repo(args.site_repo)
        ensure_site_repo(args.site_repo)
        work = args.build_dir.resolve()
        mirror = work / "rig.git"
        sources.fetch_rig(args.rig, mirror)
        cache = work / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        specs = sources.list_versions(mirror)
        config = None
        for spec in specs:
            config = build_version(spec, mirror, work, cache, args.theme.resolve(),
                          args.transforms.resolve(), args.site_repo.resolve())
        if any(s["aliases"] for s in specs):
            _run(_mike("set-default", "--deploy-prefix", "docs", "-F", str(config),
                       "latest"),
                 args.site_repo.resolve(), "mike set-default")
    except BuildError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
