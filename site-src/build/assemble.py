"""Assemble one version's docs dir, config and theme."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import yaml

from context import BuildError, VersionContext
from links import rewrite_links

SITE_URL = "https://aindriub.github.io/rig-site/docs/{id}/"

# Copied from data-prism's mkdocs.yml.
VALIDATION = {
    "nav": {"omitted_files": "warn", "not_found": "warn", "absolute_links": "warn"},
    "links": {"not_found": "warn", "absolute_links": "warn",
              "unrecognized_links": "warn", "anchors": "warn"},
}

MARKDOWN_EXTENSIONS = [
    "admonition",
    "pymdownx.details",
    "pymdownx.superfences",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "tables",
    "attr_list",
    "md_in_html",
    {"toc": {"permalink": True}},
]

DEV_NOTICE = (
    '!!! warning "Unreleased"\n'
    "    This documentation is built from rig `main`. It describes changes that "
    "may not be in any release yet.\n\n"
)


def install_theme(build_dir: Path, docs_dir: Path, theme_src: Path) -> None:
    if not (theme_src / "mkdocs.theme.yml").is_file():
        raise BuildError(f"{theme_src}: no mkdocs.theme.yml")
    theme_dst = build_dir / "theme"
    theme_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(theme_src / "mkdocs.theme.yml", theme_dst / "mkdocs.theme.yml")
    if (theme_src / "overrides").is_dir():
        shutil.copytree(theme_src / "overrides", theme_dst / "overrides")
    if (theme_src / "assets").is_dir():
        shutil.copytree(theme_src / "assets", docs_dir / "assets" / "theme")


def assemble_pages(ctx: VersionContext) -> None:
    src = ctx.source_dir
    if not (src / "README.md").is_file():
        raise BuildError(f"{ctx.ref}: README.md: missing")
    published = {"README.md": "index.md"}
    docs = src / "docs"
    if docs.is_dir():
        for p in sorted(docs.glob("*.md")):
            if p.is_file() and not p.name.startswith("phase-"):
                published[f"docs/{p.name}"] = p.name
    ctx.docs_dir.mkdir(parents=True)
    for source, page in published.items():
        text = (src / source).read_text(encoding="utf-8")
        new = rewrite_links(text, source, published, ctx.blob_base)
        (ctx.docs_dir / page).write_text(new, encoding="utf-8")


def run_transforms(ctx: VersionContext, transforms_dir: Path) -> None:
    for path in sorted(transforms_dir.glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"rig_transform_{path.stem}", path)
        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as exc:
            raise BuildError(f"{path}: transform failed to load: {exc!r}") from exc
        if not callable(getattr(mod, "apply", None)):
            raise BuildError(f"{path}: transform has no apply(ctx)")
        try:
            mod.apply(ctx)
        except Exception as exc:
            raise BuildError(f"{path}: transform failed on {ctx.id}: {exc!r}") from exc


def add_dev_notice(ctx: VersionContext) -> None:
    index = ctx.docs_dir / "index.md"
    index.write_text(DEV_NOTICE + index.read_text(encoding="utf-8"), encoding="utf-8")


def write_config(ctx: VersionContext, nav: list) -> Path:
    config = {
        "INHERIT": "theme/mkdocs.theme.yml",
        "site_name": "rig",
        "site_url": SITE_URL.format(id=ctx.id),
        "repo_url": "https://github.com/AindriuB/rig",
        "edit_uri": "",
        "strict": True,
        "validation": VALIDATION,
        "plugins": ["search"],
        "extra": {"version": {"provider": "mike"}, "generator": False},
        "markdown_extensions": MARKDOWN_EXTENSIONS,
        "nav": nav,
    }
    path = ctx.build_dir / "mkdocs.yml"
    path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    return path
