# Release runbook

rig-site has no versioned releases: no version bump, no tag, no registry.
Publishing is the `pages` workflow (`.github/workflows/pages.yml`), which
builds the site and pushes `gh-pages`. It runs on:
- push to `main`
- `repository_dispatch` type `rig-release` (rig's `release: published`)
- `workflow_dispatch` (manual: `gh workflow run pages.yml`)

## Verify the published state
- `gh run list --workflow pages.yml` shows the latest run `completed success`.
- `curl -s -o /dev/null -w '%{http_code}\n' https://aindriub.github.io/rig-site/docs/latest/`
  prints `200`.

## If a step fails
- Fix forward with a new commit to `main`, or re-run with `workflow_dispatch`.
- Never write the repository's own `gh-pages` ref by hand; see `conventions.md`.
