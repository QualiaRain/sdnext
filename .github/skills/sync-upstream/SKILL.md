---
name: sync-upstream
description: "Update this fork from upstream vladmandic/sdnext: fetch, merge master or dev, keep fork-local files, restore submodule pins, verify startup and lint, refresh fork-local agent guidance, and push to the working branch."
argument-hint: "Optionally 'master' (default, releases) or 'dev' (newer, less tested)"
---

# Sync The Fork With Upstream

Bring the fork's working branch up to date with upstream SD.Next while keeping the fork-local files and without disturbing the fork's own `master` and `dev` branches.

## When To Use

- The user asks to update SD.Next, pull upstream, or sync the fork
- Before a performance or audit pass, so that the work starts from current code

## Guidance

- Before merging, sort what the fork carries into two kinds:
  - fork-only files, which upstream does not have (for example `CLAUDE.md` and fork skills): `git diff --name-only --diff-filter=A upstream/master...HEAD`
  - upstream files the fork has changed (for example landed fixes): `git diff --name-only --diff-filter=M upstream/master...HEAD`
- Work on the session's working branch. Do not push to the fork's `master` or `dev` without explicit permission, and do not open a pull request unless asked.

## Steps

1. Remote: `git remote get-url upstream || git remote add upstream https://github.com/vladmandic/sdnext`.
2. Fetch. Cloud checkouts are often shallow; fetch enough history to find the merge base, for example `git fetch upstream master dev --shallow-since=<date a little before the last sync>`, or `git fetch --unshallow` when time allows. Check with `git merge-base HEAD upstream/master`.
3. Choose the source. The fork's precedent is to merge `upstream/master` (releases). `upstream/dev` is ahead and less tested; report how many commits ahead it is (`git rev-list --count upstream/master..upstream/dev`) and use it only when the user asks.
4. Merge: `git merge --no-edit upstream/master`.
   - Conflicts in fork-only files: keep the fork's version and update it where upstream renamed or moved what it describes.
   - Conflicts in upstream files the fork changed: resolve hunk by hunk, keeping the intent of both sides. Never take the fork's whole file, which would drop upstream's changes. If upstream already made the same fix, keep upstream's version. Rerun the fork change's own checks afterwards.
5. Submodules: `git submodule update --init --recursive` moves them to the new pins. Do not commit submodule pointer changes made by the installer: a full-path launch fast-forwards submodules to their branch heads, and committing that would diverge the fork from upstream's pins (`installer.py` also pins `sdnq_target`). Restore with `git submodule update --checkout <paths>`.
6. Check the result: `git diff --stat upstream/master HEAD` should list only the fork-only files and the upstream files the fork changed, as sorted before the merge.
7. Verify:
   - startup self-test: `./webui.sh --uv --test` (as root `./webui.sh -f --uv --test`, with `-f` first), or `python launch.py --test --port <free>` when a server is already running
   - lint as in the `fix-lint` skill, at least `ruff check` and `pylint` on changed modules
   - with a server and the tiny model from `perf-sandbox`, `e2e.py` should run without errors (hashes may legitimately change across upstream versions; take a new reference afterwards)
8. Refresh fork-local guidance. Check `package.json` scripts, `.github/instructions/`, `.github/skills/README.md` and the folder layout against `CLAUDE.md`, and fix what upstream renamed or moved. Commit that separately from the merge.
9. Push the branch with retries on network errors. Report the upstream commit merged, the number of commits brought in, what changed for users (from the changelog), the verification results, and how far `upstream/dev` is ahead.

## Output

The merge commit, the guidance commit if any, verification results, and the sync summary for the user.
