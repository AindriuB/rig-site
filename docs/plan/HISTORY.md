# History

What was built, newest first. Append-only. Only `scribe` edits this file.

**Read this before redesigning anything.** The `Cost` line on each entry is the
point of the file — it is where the sessions that already tried the obvious
approach tell you what happened.

Do not load this file to find out whether something exists. It grows without
bound. `HISTORY-INDEX.md` carries one row per entry; scan that, then grep this
file for the exact heading it names. Every entry added here gets its index row
in the same commit.

<!--
## YYYY-MM-DD — <what landed>
<Two or three sentences: what it does now that it did not before.>
**Cost:** <what was hard, what was tried and abandoned, what not to retry.>
-->

## 2026-11-24 — Offline Mermaid rendering
`transforms/50_mermaid.py` and `site-src/build/mermaid/` replace every ```` ```mermaid ```` fence with a light and a dark SVG, rendered offline in the pinned mermaid-cli image (`--network none`, `-b transparent`) with rig-palette configs and swapped by scheme through `#only-light` / `#only-dark`. SVGs are cached by the hash of the fence, the config bytes and the image pin; a fence without `%% alt:` or a render error fails the build with page and line.
**Cost:** Two review rounds; the AC3 colour scan was widened from the theme variables to the whole config (f-rs3n) and rendered SVGs are now validated for `foreignObject`, scripts and external URLs. Follow-ups, all open: f-drha (P3) a fence indented 4 or more spaces, such as inside an admonition, is skipped silently and fails only later in task 08 with no page:line, so decide whether to render it with its indent or fail the build (`render.py:20`); f-fdg2 (P3) the cache key omits the docker flags, so changing `docker_argv` serves stale SVGs from a persistent local `.build/cache`; CI is unaffected (`render.py:64`); f-r5zg (P3) the colour scan in `test_mermaid.py:163` misses upper-case function names, `color()` and CSS system colours, so compile with `re.I` and extend the lists; f-r6fy (NOTE) `validate_svg` matches `https?://` case-sensitively and checks only cache misses (`render.py:91`). None occurs in a current rig ref.

## 2026-11-24 — Unversioned changelog page
`site-src/changelog/build.py` builds rig `main`'s `CHANGELOG.md` into a strict MkDocs page at `/rig-site/changelog/` in the shared theme, with relative links rewritten to blob URLs on `main` and links back to the landing page and docs. If rig `main` has no `CHANGELOG.md` it builds a placeholder page linking to GitHub releases and prints `::warning::`.
**Cost:** The first `rig task finish` was refused because an untracked `.venv2/` in the worktree counted as uncommitted changes; the stray environment was removed and finish re-run with the same sha. The worktree `.venv` also had to be rebuilt with python3.12 from `site-src/requirements.txt` (f-g622, environment only). No open findings.

## 2026-11-24 — Lifecycle diagram from each version's basic preset
`site-src/build/lifecycle.py` converts a version's `basic.json` preset into a `stateDiagram-v2` fence with a generated `%% alt:` line, and `transforms/30_lifecycle.py` inserts it at the end of the "## The `basic` preset" section of that version's `workflows.md`. Versions without `workflows.md` (v0.1.0) are skipped; a missing preset or heading fails naming the version.
**Cost:** The 04 fence contract said one-sentence alt text, but an alt naming every state and route needs several, so the contract was amended to a single-line alt (f-6g0r). Follow-ups, all open: f-1zbs (P3) `test_inserts_when_section_is_last` asserts only `endswith(fence)` so the newline handling at `30_lifecycle.py:31-32` is unguarded (`test_lifecycle.py:72`); f-q2vc (NOTE) the section scan is not fence-aware, so a `## ` line inside a code fence in the basic section would end it early, unreachable at any current rig ref (`30_lifecycle.py:27`).

## 2026-11-24 — Site guards
`site-src/checks/check_site.py` fails the build on external script or image references and checks the version page names and bundle allowlist; `check_actions_pinned.py` refuses any workflow `uses` that is not a pinned ref, scanning both `*.yml` and `*.yaml`.
**Cost:** The actions-pin reader is line-based and took three review rounds of patching YAML shapes one at a time (f-4waa); the settled rule is fail closed, so an unreadable `uses` layout is refused rather than passed. Do not add more per-shape patches; if it needs more, use a real YAML parser. A `.pytest_cache/` was committed by accident (f-27my) and removed. Follow-ups, all open: f-yf2h (P3) the external-URL normaliser does not strip leading C0 controls as WHATWG does, so a raw `\x01//cdn...` src exits 0 (`check_site.py:39`); f-vrbn (P3) the duplicate-attribute tests lack the `returncode == 1` assertion (`test_check_site.py:104`); f-2aqy (P3) a `uses` value with a trailing `,`, `'`, `#` or `}` is read as a prefix and a mutable ref passes (`check_actions_pinned.py:9`); f-afm3 (NOTE) two tests check two behaviours each against `docs/conventions.md` (`test_check_site.py:13`, `:85`). 09-changelog-page was verified in the same wave but is not merged yet.

## 2026-11-24 — Versioned docs pipeline
`site-src/build/` now assembles each rig version's docs from its git ref (`sources.py`, `assemble.py`, `links.py`, `nav.py`, `context.py`) and deploys every version with mike (`versions.py`) into a scratch site repo under `.build/`, never this repository's own `gh-pages`. Relative links are rewritten to blob URLs at the ref and relative image references fail the build.
**Cost:** Review fixed several link-rewrite bypasses (f-bn3s among them); the image-reference refusal is regex-based and still has gaps, so a parser-based check may be the next step rather than more regexes. Follow-ups, all open: f-q8hy (P3, raised by f-3fey NOTE) a missing `--transforms` dir is skipped silently and exits 0, a `docs/conventions.md` Errors break to fix before 04 and 05 add transforms (`assemble.py:67`); f-a9kh (P3) `unquote()` leaves raw spaces in rewritten link destinations (`links.py:103`); f-9b8s (P3) nav titles strip emphasis markers inside code spans (`nav.py:18`); f-w8fb (P3) raw HTML `<img>` with a relative src is neither refused nor rewritten (`links.py:153`); f-dmvq (P3) image-ref refusal bypassed by whitespace runs in labels and `![p] [x]` (`links.py:14`); f-qzch (NOTE) subprocesses inherit `GIT_DIR`/`GIT_WORK_TREE`, so drop them from the subprocess env (`versions.py:62`). None occurs in any current rig ref.

## 2026-11-24 — rig identity and Material theme
`site-src/theme/` now holds one token file (`tokens.css`, dark and light sets, signal-amber accent), self-hosted IBM Plex fonts with OFL text and sha256 sources, the lowercase `rig` wordmark and three-dot mark, `mkdocs.theme.yml` and overrides for the build to inherit. `site-src/checks/check_contrast.py` proves the contrast pairs in both sets and exits 1 naming failures.
**Cost:** Review round 1 fixes landed on the branch. The contrast script's `REQUIRED` list covers only the 11 tokens in the AC5 pairs, so `--rig-code-bg` and the font tokens can vanish from the light set unnoticed. Follow-ups, all open: f-48xr (NOTE) add code-bg and font tokens to the required set or cover them in the 08 guards (`check_contrast.py:31`); f-hr3e (NOTE) commit 5a851ab subject uses the slug rather than `<task-id>:` per `docs/conventions.md:15`, left as is because history is already merged.

## 2026-11-24 — Kit scaffold filled and toolchain pinned
`docs/conventions.md`, `docs/architecture.md` and `docs/release.md` now describe rig-site: the directory layout later tasks build into, repository topology, the release-to-Pages flow and the pytest and error-reporting rules. `site-src/requirements.txt` pins mkdocs, mkdocs-material, mike, pymdown-extensions and pytest, and `.gitignore` covers build scratch and worktrees.
**Cost:** Nothing abandoned. The pipeline must never write this repository's own `gh-pages` ref, because worktrees share refs: mike runs against a scratch repo under `.build/`. Do not use a default-deny `/*` rule in `.gitignore`.
