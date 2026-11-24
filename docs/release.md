# Release runbook

<!-- Read by /ship. Keep it under 30 lines: commands and checks, no prose. -->

## Version bump
- Files: <e.g. pom.xml, Cargo.toml, package.json> — set to `<version>`.
- Commit: `release: <version>` on a `release/<version>` branch; PR to `<default>`.
- Wait: CI `<workflow file>` green on the PR, then merge.

## Tag
- `git tag -a v<version> -m "<version>"` on the merge commit, then `git push origin v<version>`.

## Publish targets
| Target | Triggered by | Workflow | Secret it needs |
|---|---|---|---|
| <GitHub release> | tag push | `<release.yml>` | none |
| <registry, e.g. Maven Central> | <release published> | `<publish.yml>` | `<NAME>` |
| <image, e.g. ghcr.io/owner/app> | <tag push> | `<image.yml>` | `<NAME>` |

## Verify the published state
- GitHub release: `gh release view v<version>` lists the assets.
- Registry: `<command that shows version <version> is live>`.
- Image: `docker manifest inspect <image>:<version>` succeeds.

## If a step fails
- Do not delete or move a pushed tag. Fix forward with `<version+patch>`.
