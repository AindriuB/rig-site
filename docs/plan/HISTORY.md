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

## 2026-11-24 — Versioned docs pipeline
`site-src/build/` now assembles each rig version's docs from its git ref (`sources.py`, `assemble.py`, `links.py`, `nav.py`, `context.py`) and deploys every version with mike (`versions.py`) into a scratch site repo under `.build/`, never this repository's own `gh-pages`. Relative links are rewritten to blob URLs at the ref and relative image references fail the build.
**Cost:** Review fixed several link-rewrite bypasses (f-bn3s among them); the image-reference refusal is regex-based and still has gaps, so a parser-based check may be the next step rather than more regexes. Follow-ups, all open: f-q8hy (P3, raised by f-3fey NOTE) a missing `--transforms` dir is skipped silently and exits 0, a `docs/conventions.md` Errors break to fix before 04 and 05 add transforms (`assemble.py:67`); f-a9kh (P3) `unquote()` leaves raw spaces in rewritten link destinations (`links.py:103`); f-9b8s (P3) nav titles strip emphasis markers inside code spans (`nav.py:18`); f-w8fb (P3) raw HTML `<img>` with a relative src is neither refused nor rewritten (`links.py:153`); f-dmvq (P3) image-ref refusal bypassed by whitespace runs in labels and `![p] [x]` (`links.py:14`); f-qzch (NOTE) subprocesses inherit `GIT_DIR`/`GIT_WORK_TREE`, so drop them from the subprocess env (`versions.py:62`). None occurs in any current rig ref.

## 2026-11-24 — rig identity and Material theme
`site-src/theme/` now holds one token file (`tokens.css`, dark and light sets, signal-amber accent), self-hosted IBM Plex fonts with OFL text and sha256 sources, the lowercase `rig` wordmark and three-dot mark, `mkdocs.theme.yml` and overrides for the build to inherit. `site-src/checks/check_contrast.py` proves the contrast pairs in both sets and exits 1 naming failures.
**Cost:** Review round 1 fixes landed on the branch. The contrast script's `REQUIRED` list covers only the 11 tokens in the AC5 pairs, so `--rig-code-bg` and the font tokens can vanish from the light set unnoticed. Follow-ups, all open: f-48xr (NOTE) add code-bg and font tokens to the required set or cover them in the 08 guards (`check_contrast.py:31`); f-hr3e (NOTE) commit 5a851ab subject uses the slug rather than `<task-id>:` per `docs/conventions.md:15`, left as is because history is already merged.

## 2026-11-24 — Kit scaffold filled and toolchain pinned
`docs/conventions.md`, `docs/architecture.md` and `docs/release.md` now describe rig-site: the directory layout later tasks build into, repository topology, the release-to-Pages flow and the pytest and error-reporting rules. `site-src/requirements.txt` pins mkdocs, mkdocs-material, mike, pymdown-extensions and pytest, and `.gitignore` covers build scratch and worktrees.
**Cost:** Nothing abandoned. The pipeline must never write this repository's own `gh-pages` ref, because worktrees share refs: mike runs against a scratch repo under `.build/`. Do not use a default-deny `/*` rule in `.gitignore`.
