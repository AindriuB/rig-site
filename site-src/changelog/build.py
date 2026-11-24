"""Build the unversioned changelog page from rig `main`'s CHANGELOG.md."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "site-src" / "build"))

import assemble  # noqa: E402
import sources  # noqa: E402
import yaml  # noqa: E402
from context import RIG_BLOB, BuildError  # noqa: E402
from links import rewrite_links  # noqa: E402
from versions import DEFAULT_RIG  # noqa: E402

SITE_URL = "https://aindriub.github.io/rig-site/changelog/"
RELEASES = "https://github.com/AindriuB/rig/releases"
NAV_LINKS = '<p><a href="../">rig home</a> &middot; <a href="../docs/">Documentation</a></p>\n\n'
MISSING = (
    "# Changelog\n\n"
    "The changelog is not yet published. See rig's "
    f"[GitHub releases]({RELEASES}) for release notes.\n"
)


def read_changelog(mirror: Path) -> str | None:
    """Return CHANGELOG.md at `main`, or None if `main` has no such file."""
    git = ["git", "--git-dir", str(mirror)]
    r = subprocess.run([*git, "rev-parse", "--verify", "-q", "refs/heads/main"],
                       capture_output=True, text=True)
    if r.returncode:
        raise BuildError(f"{mirror}: rig has no main branch")
    r = subprocess.run([*git, "cat-file", "-e", "refs/heads/main:CHANGELOG.md"],
                       capture_output=True, text=True)
    if r.returncode:
        return None
    r = subprocess.run([*git, "show", "refs/heads/main:CHANGELOG.md"], capture_output=True)
    if r.returncode:
        raise BuildError(f"git show CHANGELOG.md: {r.stderr.decode().strip()}")
    return r.stdout.decode("utf-8")


def build(out: Path, rig: str, theme: Path, work: Path) -> None:
    mirror = work / "rig.git"
    sources.fetch_rig(rig, mirror)
    text = read_changelog(mirror)
    if text is None:
        print("::warning::rig main has no CHANGELOG.md; building the placeholder page")
        body = MISSING
    else:
        body = rewrite_links(text, "CHANGELOG.md", {"CHANGELOG.md": "index.md"},
                             f"{RIG_BLOB}main/")
    build_dir = work / "changelog"
    if build_dir.exists():
        import shutil
        shutil.rmtree(build_dir)
    docs_dir = build_dir / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "index.md").write_text(NAV_LINKS + body, encoding="utf-8")
    assemble.install_theme(build_dir, docs_dir, theme)
    config = {
        "INHERIT": "theme/mkdocs.theme.yml",
        "site_name": "rig",
        "site_url": SITE_URL,
        "repo_url": "https://github.com/AindriuB/rig",
        "edit_uri": "",
        "strict": True,
        "validation": assemble.VALIDATION,
        "plugins": ["search"],
        "extra": {"generator": False},
        "markdown_extensions": assemble.MARKDOWN_EXTENSIONS,
        "nav": [{"Changelog": "index.md"}],
    }
    cfg = build_dir / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
                   encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "mkdocs", "build", "-q", "-f", str(cfg),
                        "-d", str(out)], capture_output=True, text=True)
    if r.returncode:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise BuildError(f"{cfg}: mkdocs build failed (exit {r.returncode})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rig", default=DEFAULT_RIG)
    ap.add_argument("--theme", type=Path, default=ROOT / "site-src" / "theme")
    ap.add_argument("--build-dir", type=Path, default=ROOT / ".build",
                    help="scratch area for the rig mirror and the generated site source")
    args = ap.parse_args(argv)
    try:
        build(args.out.resolve(), args.rig, args.theme.resolve(), args.build_dir.resolve())
    except BuildError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
