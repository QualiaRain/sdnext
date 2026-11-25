#!/bin/bash
# Create an isolated, complete working copy of SD.Next for measuring or testing a change.
# The copy is a git worktree with its own submodule checkouts (cloned from the local object store, no network),
# symlinks to the main checkout's venv and node_modules, and a copy of its config.json.
# Nothing done in the copy touches the main checkout's working tree. Calling it again with the same name returns the same copy.
#
# Usage: mkwt.sh <name>        prints the path of the copy on its last line
# Env:   BASE=<commit>         commit to check out (default: HEAD of the main checkout)
#        SD_WT_ROOT=<dir>      folder that holds the copies (default: <parent of the main checkout>/wt)
# Needs git >= 2.31. Uses flock when available so that many agents can call it at once.
set -uo pipefail
NAME="${1:?usage: mkwt.sh <name>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON="$(git -C "$HERE" rev-parse --path-format=absolute --git-common-dir)" || exit 1
MAIN="$(dirname "$COMMON")"
BASE="${BASE:-$(git -C "$MAIN" rev-parse HEAD)}"
ROOT="${SD_WT_ROOT:-$(dirname "$MAIN")/wt}"
WT="$ROOT/$NAME"
if [ -e "$WT/.wt-ready" ]; then echo "$WT"; exit 0; fi
mkdir -p "$ROOT"
if command -v flock >/dev/null 2>&1; then
  exec 9>"$ROOT/.mkwt.lock"
  flock -w 300 9 || { echo "could not get the worktree lock" >&2; exit 1; }
fi
if [ ! -d "$WT" ]; then
  git -C "$MAIN" worktree add --detach "$WT" "$BASE" >/dev/null 2>&1 || { echo "worktree add failed: $WT at $BASE" >&2; exit 1; }
fi
cd "$WT" || exit 1
for p in $(git config -f .gitmodules --get-regexp 'submodule\..*\.path' | awk '{print $2}'); do
  url=$(git config -f .gitmodules --get "submodule.$p.url")
  if [ -d "$COMMON/modules/$p" ]; then
    git -c protocol.file.allow=always -c "submodule.$p.url=$COMMON/modules/$p" submodule update --init -- "$p" >/dev/null 2>&1 \
      || git submodule update --init -- "$p" >/dev/null 2>&1 \
      || { echo "submodule init failed: $p" >&2; exit 1; }
  else
    git submodule update --init -- "$p" >/dev/null 2>&1 || { echo "submodule init failed: $p" >&2; exit 1; }
  fi
  git -C "$p" remote set-url origin "$url" 2>/dev/null
done
[ -e venv ] || ln -s "$MAIN/venv" venv
[ -e node_modules ] || ln -s "$MAIN/node_modules" node_modules
[ -e config.json ] || { [ -f "$MAIN/config.json" ] && cp "$MAIN/config.json" config.json; }
mkdir -p tmp
# keep the helper links out of `git status`; info/exclude is shared by all worktrees of the repository, which is harmless because the main checkout ignores these paths anyway
excl=$(git rev-parse --git-path info/exclude)
mkdir -p "$(dirname "$excl")"
grep -qs '^/venv$' "$excl" || printf '/venv\n/node_modules\n/.wt-ready\n' >> "$excl"
touch .wt-ready
echo "$WT"
