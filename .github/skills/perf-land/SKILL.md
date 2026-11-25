---
name: perf-land
description: "Apply reviewed performance patches to the working branch as atomic, verified commits: apply in order, rebuild UI bundles when needed, lint, run the app and the bit-exact end-to-end check on the combined result, write accurate commit messages, push, and report what was held back or rejected."
argument-hint: "Patch files or candidate ids accepted by the perf-patch reviewer"
---

# Land Performance Patches

Turn accepted patches into one commit each on the working branch, verify the combined result, and push.

## When To Use

- After `perf-patch` reviewers accepted patches (verdict `accept` or `accept-with-changes`)
- When cherry-picking performance commits onto another branch, for example one cut from upstream `dev`

## Guidance

- Follow the branch, commit and attribution rules in `CLAUDE.md` (fork-local AI-generated commits carry the trailer named there). Never put model names in commit messages or code.
- Use the `perf-sandbox` skill for the verification run.
- Patches with verdict `needs-decision`, and anything the reviewer rejected, are not committed. Report them to the user with the exact behavior change and the patch path.

## Steps

1. Start clean. `git status --porcelain` must be empty. If the only changes are submodule pointers moved by the installer (a full-path launch fast-forwards them), restore the pins with `git submodule update --checkout <submodule paths>` instead of committing them.
2. Choose the order: independent patches first, stacked parts (`.1`, `.2`) in order, `.v2` files instead of the originals when the reviewer corrected a patch.
   Choose the granularity with the user: one commit per fix (easiest to cherry-pick upstream) or themed commits (one per area such as page load, startup, generation, installer). For a themed commit, apply and check each patch on its own first, then commit them together with a body that lists every change with its own measured effect.
3. For each candidate:
   - `git apply --3way <patch>`; check `git diff --stat` lists only the intended files.
   - If `ui/*.ts` changed, rebuild with `pnpm run build:core` (Node 24 or newer) and include `ui/dist/sdnext.mjs` and its map in the same commit. Run `eslint:core` and `tsc:core`.
   - Lint changed Python files with `venv/bin/ruff check <files>` and `venv/bin/pylint <files>`; no new findings.
   - Run the offline tests in `test/` that touch the changed modules.
   - Stage by explicit path (`git add <files>`), never `git add -A` or `commit -a`.
   - Commit with the reviewed message: a conventional subject (`perf(<area>): ...`, `fix(<area>): ...`), and a body that says what changed, why it is safe, and the measured effect with how it was measured. Correct any number the reviewer disputed.
4. Verify the combined result once all commits of the batch are in:
   - fresh copy at the new head: `BASE=$(git rev-parse HEAD) bash .github/skills/perf-sandbox/scripts/mkwt.sh land-check-<n>`
   - `run-app.sh` on it, compare its log with a start of the previous head for new errors or warnings
   - `e2e.py --compare <reference>` must report identical hashes
   - a `launch.py --test --port <free>` run on the copy
   If anything fails, find the commit with the same procedure on intermediate heads, and drop or fix it before pushing.
5. Push the branch (`git push -u origin <branch>`; retry network errors with backoff). Do not push to other branches and do not open a pull request unless the user asks.
6. Report: per commit the measured gain and method; per held or rejected candidate the reason; what could not be validated (for example GPU-only paths) and how the user can validate it.

## Upstreaming

Branches meant for upstream pull requests are cut from upstream `dev`, never from the fork branch, and carry one change each (CONTRIBUTING asks for one clear change per contribution). A themed commit is not sent as is: rebuild each of its changes on its own branch from the reviewed patch file, or split the commit, resolve against `dev`, and repeat steps 3 and 4 there, since `dev` differs. Changes that alter the data flow between Gradio and the frontend need the maintainers' agreement first (rule 1 of `.github/instructions/ui.instructions.md`): say so in the pull request text. Read `.github/skills/ai-disclosure/SKILL.md` in full before preparing any upstream-facing text; CLAUDE.md makes that mandatory. If that file is missing, stop and ask the user before writing any upstream-facing text.

## Output

The list of commits pushed (hash, subject, measured effect), the candidates held for a decision or rejected with reasons, and the verification results.
