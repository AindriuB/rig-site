# Architecture

The shape of the system: what the pieces are, what talks to what, and where the
boundaries are. `explorer` and `architect` read this before inferring
structure from the filesystem, so keeping it honest saves every session a
search.

rig-site builds the public site for rig: a hand-built landing page, versioned
docs, and a changelog, published to GitHub Pages.

## Components

| Directory | Contents |
|---|---|
| `site-src/build/` | Versioned docs pipeline (Python): rig checkout, assembly, nav, link rewrite, transforms, mike deploy |
| `site-src/build/transforms/` | Per-version transforms, `NN_name.py`, run in filename order (lifecycle `30_`, mermaid `50_`) |
| `site-src/theme/` | Identity: `mkdocs.theme.yml`, `overrides/`, `assets/` (tokens, fonts, brand marks) shared by docs, changelog and landing |
| `site-src/landing/` | Hand-built landing page (HTML/CSS/JS, no framework) and its small include step |
| `site-src/changelog/` | One unversioned MkDocs page from rig `main`'s `CHANGELOG.md` |
| `site-src/checks/` | Guard scripts `check_*.py`, each run from the repo root |
| `.build/` | Scratch: rig clone, per-version build dirs, scratch gh-pages repo. Never committed |
| `docs/` | The kit's planning tree. Nothing under it reaches the built site |

## Repository topology

rig-site is one repository (`AindriuB/rig-site`). It builds from a second
repository, rig, which is not tracked here: the pipeline clones rig over HTTPS
at build time into `.build/`, and `.build/` is ignored.

`.claude/` is untracked on purpose: it holds the worktree scripts installed from
the agent-kit repo, whose single clone lives outside every project it serves and
is refreshed with `git -C <kit> pull`. The roles themselves are not here at all —
`agents/` and `commands/` are symlinked into `~/.claude`, shared by every
project. Tracking any of it here would fork the harness away from that upstream.

| Repo | Role | Tracked here? |
|---|---|---|
| `AindriuB/rig-site` | Site sources and pipeline | this repository |
| `AindriuB/rig` | Source of the docs and changelog; cloned (HTTPS) into `.build/` | no |

## How they talk

rig `release: published` → `repository_dispatch` type `rig-release` →
`pages.yml` → `gh-pages` → GitHub Pages. rig calls rig-site; rig-site only
reads rig. `pages.yml` also runs on push to `main` and `workflow_dispatch`.

Public URL: `https://aindriub.github.io/rig-site/`, with four paths:
- `/rig-site/` — landing page.
- `/rig-site/docs/<minor>/` — one mike version per minor; `latest` alias and
  default point at the newest released minor.
- `/rig-site/docs/dev/` — built from rig `main`, labelled unreleased.
- `/rig-site/changelog/` — from rig `main`'s `CHANGELOG.md`.

## Boundaries that must not be crossed

- Nothing under `docs/` appears in the built site.
- No third-party fonts, scripts or analytics.
- No Mermaid JS is shipped: diagrams are rendered at build time.
- The pipeline never writes this repository's own `gh-pages` ref; mike runs
  against a scratch repo under `.build/`.

## Decisions worth knowing

- 2026-11-24: MkDocs Material + `mike` in rig-site, with pinned Python
  requirements as in data-prism.
- 2026-11-24: Changelog is a Keep a Changelog `CHANGELOG.md` in rig, rendered
  from rig `main` as one unversioned page.
- 2026-11-24: Identity is rig's own, not Ascend and not data-prism's palette.
- 2026-11-24: Rebuild trigger is rig's `release: published`, not tag push,
  because rig's `release.yml` creates drafts.
