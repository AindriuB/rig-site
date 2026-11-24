#!/usr/bin/env bash
# Build every docs version, the landing page and the changelog into a scratch
# gh-pages, run every guard over the result, and push only with --push.
#
# Env: RIG_SITE_REMOTE (default: this repo's origin) is where gh-pages is
# fetched from and pushed to. RIG_URL overrides the rig repository.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"

PUSH=0
case "${1:-}" in
  "") ;;
  --push) PUSH=1 ;;
  *) echo "usage: build.sh [--push]" >&2; exit 2 ;;
esac

PY="${PYTHON:-python3}"
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; fi
LYCHEE_IMAGE="lycheeverse/lychee:0.24.2"
BUILD="$ROOT/.build"
SITE_REPO="$BUILD/site-repo"
TREE="$BUILD/site-tree"
REMOTE="${RIG_SITE_REMOTE:-$(git -C "$ROOT" remote get-url origin)}"
RIG_ARGS=()
if [ -n "${RIG_URL:-}" ]; then RIG_ARGS=(--rig "$RIG_URL"); fi

echo "== 1. fetch gh-pages"
if [ ! -d "$SITE_REPO/.git" ]; then
  mkdir -p "$SITE_REPO"
  git init -q "$SITE_REPO"
fi
git -C "$SITE_REPO" remote remove origin 2>/dev/null || true
git -C "$SITE_REPO" remote add origin "$REMOTE"
set +e
git ls-remote --exit-code --heads "$REMOTE" gh-pages >/dev/null 2>&1
rc=$?
set -e
case "$rc" in
  0) git -C "$SITE_REPO" fetch -q origin "+refs/heads/gh-pages:refs/heads/gh-pages" ;;
  2) echo "no gh-pages on the remote yet" ;;
  *) echo "cannot reach $REMOTE" >&2; exit 1 ;;
esac

echo "== 2. docs versions"
"$PY" "$HERE/versions.py" --site-repo "$SITE_REPO" --build-dir "$BUILD" ${RIG_ARGS[@]+"${RIG_ARGS[@]}"}

echo "== 3. landing and changelog"
"$PY" "$HERE/root.py" --site-repo "$SITE_REPO" --build-dir "$BUILD" ${RIG_ARGS[@]+"${RIG_ARGS[@]}"}

echo "== 4. export and guards"
rm -rf "$TREE"
mkdir -p "$TREE"
git -C "$SITE_REPO" archive gh-pages | tar -x -C "$TREE"
export RIG_SITE_TREE="$TREE"

# The site lives under /rig-site/, so mount it there and make its parent the root dir.
# 404.html is served from any depth, so its relative links cannot resolve in place.
docker run --rm -v "$TREE:/data-root/rig-site:ro" -w /data-root "$LYCHEE_IMAGE" \
  --offline --no-progress --exclude-path '/404\.html$' --root-dir /data-root rig-site

shopt -s nullglob
files=("$ROOT"/site-src/checks/check_*.py)
if [ "${#files[@]}" -eq 0 ]; then
  echo "no site-src/checks/check_*.py found" >&2
  exit 1
fi
while IFS= read -r f; do
  echo "== $f"
  "$PY" "$f"
done < <(printf '%s\n' "${files[@]}" | sort)

if [ "$PUSH" -eq 1 ]; then
  echo "== 5. push gh-pages"
  git -C "$SITE_REPO" push origin gh-pages
else
  echo "== 5. skipped push (no --push)"
fi
