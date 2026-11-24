# History index

One row per `## YYYY-MM-DD` entry in `HISTORY.md`, newest first. Only `scribe`
edits this file, and it writes the row in the same commit as the entry.

`HISTORY.md` grows without bound and is the single largest file a session can
accidentally load. This index exists so `planner` can answer "has this been
built before, and where do I read about it?" without opening it. Rows are taken
from `HISTORY.md`'s own headings rather than re-summarized, so the index can be
checked against its source by eye.

Read a full entry by grepping the exact string in the **Heading** column:

```
grep -n '<heading text>' docs/plan/HISTORY.md
```

Then read that section only. A stale index is worse than none — an entry with
no row is one `planner` cannot find, and will re-plan.

| Date | Task IDs | Summary | Heading (grep this exact string) |
|---|---|---|---|
| 2026-11-24 | 12, 13, 14, 15 | Closed fifteen follow-ups: motion, landing guards, render, one pytest session | ## 2026-11-24 — Follow-up sweep: motion, landing guards, render, pytest session |
| 2026-11-24 | 10 | Guarded Pages build and deploy workflow | ## 2026-11-24 — Pages deploy workflow |
| 2026-11-24 | 07 | Push, forge and state visuals on the landing page | ## 2026-11-24 — Landing visuals |
| 2026-11-24 | 06 | Landing page built from partials and captures | ## 2026-11-24 — Landing page |
| 2026-11-24 | 04 | Offline light/dark Mermaid SVG rendering with cache | ## 2026-11-24 — Offline Mermaid rendering |
| 2026-11-24 | 09 | Unversioned changelog page built from rig main | ## 2026-11-24 — Unversioned changelog page |
| 2026-11-24 | 05 | Basic-preset state diagram generated per version | ## 2026-11-24 — Lifecycle diagram from each version's basic preset |
| 2026-11-24 | 08 | Built-site and workflow-pin guard checks | ## 2026-11-24 — Site guards |
| 2026-11-24 | 03 | Per-version docs assembly and mike deploy pipeline | ## 2026-11-24 — Versioned docs pipeline |
| 2026-11-24 | 02 | Tokens, fonts, brand marks, Material theme, contrast check | ## 2026-11-24 — rig identity and Material theme |
| 2026-11-24 | 01 | Conventions, architecture and release docs filled; toolchain pinned | ## 2026-11-24 — Kit scaffold filled and toolchain pinned |
