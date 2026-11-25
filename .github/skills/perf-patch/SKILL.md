---
name: perf-patch
description: "Turn a performance finding into a verified patch: reproduce the cost, build the smallest correct change in an isolated working copy, prove gain and equivalence, then have an independent reviewer try to break it. Includes a Workflow script that runs builder and reviewer for groups of candidates."
argument-hint: "One or more finding files or candidate descriptions to build and review"
---

# Build And Attack A Performance Patch

Every candidate goes through two independent roles. The builder must first prove the problem is real, then produce a minimal tested patch. The reviewer assumes the patch is wrong and tries to show it. Nothing is committed by either role: accepted patches are applied with the `perf-land` skill.

## When To Use

- After `perf-audit` produced findings, or for any single performance change proposed by a user or an issue
- When a change touches hot paths, startup, the installer, the server or generated output, where a plausible but wrong optimization is costly

## Guidance

- Read `.github/copilot-instructions.md` and the matching file in `.github/instructions/` before editing.
- Use the `perf-sandbox` skill for working copies, servers and the end-to-end check, and the measuring rules from `perf-audit`.

## Builder Protocol

1. Refute first. Reproduce the claimed cost yourself on code paths a real user hits. If it does not reproduce, the gain is negligible for real users, or no safe narrow fix exists, stop with verdict `reject` and the evidence. A well-founded rejection is a good result.
2. Build the smallest correct patch in your own working copy (one copy per candidate, named after it). Think through every caller, threads, error paths, restart and reload flows (UI restart, server restart, model reload, extension reload), options and launch flags that change the path, extensions and API clients that may rely on current behavior, and all platforms. Prefer the variant that preserves behavior exactly.
3. Prove it:
   - before and after measurement of the gain, paired and interleaved on a noisy machine
   - equivalence: identical outputs, responses or files where they should be; the end-to-end hash check when startup, model loading, generation, saving or the server is touched
   - an app start with the patch, comparing the log with an unpatched start for new errors or warnings
   - lint: `ruff check` and `pylint` on changed Python files must not add findings compared with the unpatched files; `eslint:core`, `tsc:core` and `build:core` with pnpm for TypeScript
   - the offline tests in `test/` that touch the changed module
4. Hand over: `git -C <copy> diff HEAD -- <changed source files> > tmp/perf/patches/<id>.diff`. Use `<id>.1.diff`, `<id>.2.diff` for stacked parts, each measured on its own. Leave `ui/dist` out of the patch (it is rebuilt when landing). Confirm the patch applies to a fresh copy with `git apply --check`. Stop your server.

Verdicts: `patch` (safe and measured), `needs-decision` (the worthwhile variant changes something a user, extension or API client can observe, or it is a product choice, or it could not be validated on the hardware it targets), `reject`.

## Reviewer Protocol

1. Read the patch and everything around it: every caller, every other writer of the state it touches, and the same code on upstream dev.
2. Apply it in your own copy and attack it with concrete attempts, not opinions: changed outputs; concurrency (requests during the change, the save thread, background scans, the queue); error and partial-failure paths; restart, reload and second-invocation flows; unusual but supported options and launch flags; extensions and API clients; Windows and macOS paths; non-CUDA backends; memory growth over many iterations; whether the gain survives a realistic setup rather than the builder's benchmark.
3. Measure the gain yourself, with a different method where possible.
4. Rerun lint, tests, an app start and the end-to-end check.
5. Decide: `accept`, `accept-with-changes` (fix narrow defects yourself, write `<id>.v2.diff`, test it the same way), or `reject` with the reason. If unsure whether the patch is safe, reject. Check the proposed commit message against what you measured.

## Patch Rules

- Narrow, scoped to one function or module, matching nearby style (long lines are normal here). Short comments only where the code is not self-explanatory.
- No reordering of startup steps in `launch.py` or `webui.py`; platform neutral across CUDA, ROCm, IPEX, DirectML, OpenVINO, MPS and CPU, and Windows, macOS and Linux.
- No edits to submodules, vendored folders, generated locale files or built output.
- Logging through `from modules.logger import log` with key=value f-strings.
- GPU-only paths cannot be validated on a CPU machine: build the patch, write a self-contained validation script the owner can run on a GPU (`tmp/perf/patches/<id>-gpu-check.py`, printing before and after timings and comparing outputs), and return `needs-decision`.

## Resuming Interrupted Work

If an earlier attempt was cut off, its working copy (`wt/<id>`) and notes (`tmp/agents/<id>/`) may still exist. Look at them (`git -C <copy> diff`, scripts, notes) and reuse what holds up, but re-verify every claim yourself. Servers left running by a dead agent can be stopped with `stop-app.sh --all` or by their pid files.

## Running At Scale

`workflow.js` in this folder runs builder then reviewer for each group of candidates, as a pipeline (a group's review starts as soon as its build finishes). Run it with the Workflow tool:

- `scriptPath`: absolute path of `.github/skills/perf-patch/workflow.js`
- `args`:

```json
{
  "root": "/path/to/main/checkout",
  "findingsDir": "/path/to/main/checkout/tmp/perf/findings",
  "groups": [
    { "id": "installer-small", "port": 7950, "tier": "small", "note": "optional text for this group",
      "candidates": [ { "id": "inst-ext-listing", "title": "...", "findings": ["installer-5"], "extra": "candidate-specific notes" } ] }
  ]
}
```

- Group candidates that share code and context (same file or subsystem): one builder builds a separate patch per candidate, each in its own copy against the same base. This saves agent start-up and server launches.
- Each group uses two ports: `port` for the builder, `port + 1` for the reviewer.
- Concurrency per workflow is limited to CPUs minus two. On a 4-core, 16 GB machine run about four workflows at once; more agents mostly slow each other down.
- The workflow returns, per group, the builder results and the reviewer results per candidate. Read `journal.jsonl` in the workflow's transcript folder if a result looks empty.
- After a run, stop leftover servers with `stop-app.sh --all`.

## Output

Per candidate: verdict, measured gain with method, behavior change (or none), patch files in apply order, residual risks, and a commit subject and body ready for `perf-land`.
