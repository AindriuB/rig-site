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

## 2026-11-24 — Kit scaffold filled and toolchain pinned
`docs/conventions.md`, `docs/architecture.md` and `docs/release.md` now describe rig-site: the directory layout later tasks build into, repository topology, the release-to-Pages flow and the pytest and error-reporting rules. `site-src/requirements.txt` pins mkdocs, mkdocs-material, mike, pymdown-extensions and pytest, and `.gitignore` covers build scratch and worktrees.
**Cost:** Nothing abandoned. The pipeline must never write this repository's own `gh-pages` ref, because worktrees share refs: mike runs against a scratch repo under `.build/`. Do not use a default-deny `/*` rule in `.gitignore`.
