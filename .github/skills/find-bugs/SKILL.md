---
name: find-bugs
description: "Run a scoped, anti-quota-filling bug hunt: lock each finder agent to one subsystem, restrict to high-evidence bug classes, forbid fix-proposals and self-grading, and treat zero findings as a valid result. Pairs with verify-bugs."
argument-hint: "Optionally name the subsystem(s) to hunt (e.g. video_models, control, processing); otherwise propose a partition"
---

# Find Bugs (Scoped Finder Pass)

Discover real, high-confidence defects in SD.Next source without manufacturing noise. This skill drives the FINDER half of the hunt. A finder RAISES candidate defects; it never GRADES them and never proposes a code change. Every candidate must then pass `verify-bugs` before it touches a PR.

## When To Use

- You want a proactive bug sweep of the codebase or a subsystem before a release or PR
- An unsupervised "find all the bugs" loop produced a long list and you need a disciplined re-run
- A new model/pipeline/UI area landed and you want a focused defect pass on it

## Guidance

- Consult `.github/instructions/core.instructions.md` for relevant core runtime guidance before proceeding.

## The Failure Mode This Skill Exists To Prevent

An unsupervised finder loop is good on its early, narrowly-scoped passes, then degrades. Once the easy real bugs are gone, later "comprehensive final scan" iterations start **manufacturing defensive guards to have something to report** — quota-filling. Observed examples that are NOT bugs:

- Guarding against `str.split()` returning an empty list (it cannot — `"".split()` is `['']`, `"".split(sep)` is `['']`)
- Adding `None` checks on values that are never `None` on the path in question
- Replacing working concurrent code with blocking code "for safety" (an active regression, not a fix)
- Wrapping already-safe attribute access in `hasattr`/`getattr` with no reachable failure

The structural fix is below: lock scope, restrict bug classes, ban fix-proposals and self-grading, and make **zero findings an explicitly acceptable answer** so an agent never invents work to fill a quota.

## Two Hard Rules For Every Finder (Read First)

These two rules are why a cold finder over-reports. Bake them verbatim into every finder prompt.

1. **A finder never proposes a code change — no fix, no deletion, no rewrite.** A finder only POINTS at suspicious code and explains why it looks wrong. The moment you write "remove these lines" or "the fix is …" you stop reading and start advocating, and advocacy is where harmful fixes are born. Deleting code is the most dangerous of all: **dead code is not the same as removable code.** A branch can be provably unreachable *and still be load-bearing intent* the author gated deliberately (see Set-Then-Guard below). Proposing the deletion is what turns a harmless dead branch into a regression. Fixes are written later, only against `verify-bugs`-confirmed REAL defects.

2. **A finder never grades its own findings and never declares success — including in any closing summary, wrap-up, or verdict block.** The verdicts REAL / WEAK / BOGUS / STALE / HARMFUL belong to `verify-bugs` alone. A finder may not use the word "REAL" (or "confirmed", "valid", "genuine defect", "high confidence") about its own candidate **anywhere in its output — not in the per-finding lines and not in a summary or sign-off** — and may not say "execution successful", "execution complete", "ready to ship", or otherwise assert its own work is done-and-correct. This is the specific slip cold finders make: the per-finding lines stay clean, then the closing summary reaches for "both findings are REAL, execution complete" — which is exactly the "all findings REAL, execution successful" pattern by which a harmful deletion once reached a fix list. Your entire output, summary included, is a list of *suspicions to be adversarially tested*, nothing stronger. End with the raw candidate list (or `NO FINDINGS`); do not append a confidence verdict on your own pass.

## Partition Strategy (Scope Each Finder To One Subsystem)

Do NOT point one agent at the whole tree. Spawn several small finder agents, **each locked to exactly one subsystem**, so each does a deep read of a bounded surface instead of a shallow pass over everything. Suggested partition (adjust to the change set):

1. `modules/processing*.py` + `modules/txt2img.py` + `modules/img2img.py` — generation core
2. `modules/control/` — control/process pipeline
3. `modules/video_models/` — video engine
4. `modules/api/` — API surface
5. `modules/ui_*.py` — UI bindings and submit wiring
6. A single model/pipeline family under `pipelines/` or `modules/` when one is in scope

Each finder gets: its file list, the bug-class whitelist below, the two hard rules above, and the zero-findings clause. Finders do not see each other's work.

## High-Evidence Bug Classes (The Only Things Finders Report)

Restrict finders to defects that are **provable by reading the code**, not stylistic or speculative:

- **Wrong variable / wrong attribute** — a value computed or logged that differs from the one actually used (e.g. metadata logged vs metadata applied)
- **Dead conditions** — branches that are always-True or always-False. **CAUTION — read the Set-Then-Guard rule below before reporting any dead branch; most dead branches that a fix would "clean up" are intentional and the fix regresses.**
- **Name typos** — misspelled attribute/key/parameter names that silently no-op or write to the wrong field. (Canonical real example: `hasattr(p, '[init_images]')` with literal brackets — always False, so the guarded block is dead. Report the typo; do NOT propose deleting the block.)
- **Mutable default arguments** — `def f(x=[])` / `={}` shared across calls
- **Undefined name / missing attribute** — use of `self.device` or similar that is never assigned on that path → `AttributeError`
- **Missing type guard before a type-specific op** — calling `len()` / indexing / iterating a value that a reachable path can leave `None` (or a non-sequence), where the signature or a caller proves the bad type occurs (e.g. `while len(prompts_2) < n:` when `prompts_2: list | None = None` and a caller passes `None`). Report the reachable `None`/wrong-type path; this is a crash, not a defensive-guard suggestion.
- **Double application** — the same transform applied twice (e.g. a normalization run once by the caller and again by the callee)

Explicitly OUT of scope for finders (these are where quota-filling lives):
- Defensive guards against conditions that cannot occur
- Style, naming, formatting, "could be cleaner"
- Performance speculation without a concrete correctness defect
- Behavioral changes to working concurrency/threading

### Set-Then-Guard: the dead-branch trap (mandatory before reporting any dead condition)

The single most common way a finder manufactures a *harmful* candidate is the **set-then-guard** shape: a flag/attribute is assigned unconditionally, and a few lines later a branch tests it and is therefore always dead. Example actually mis-reported by a cold finder:

```
p.is_hr_pass = True            # set unconditionally
if hasattr(p, 'init_hr'):
    p.init_hr(...)
else:
    if not p.is_hr_pass:       # always False here -> the block below is "dead"
        p.hr_scale = p.scale_by        # img2img-only attributes
        p.hr_upscaler = p.resize_name
        ...
```

The `if not p.is_hr_pass:` block is genuinely unreachable on this path. But it is a **deliberate guard** ("fake hires for img2img if not actual hr pass"), and "removing the dead check so the block always runs" would execute img2img-only attribute writes (`p.scale_by`, `p.resize_name`) on a txt2img pass where those attributes may not exist → `AttributeError` / wrong output. That is an active regression, not a fix.

Rules when you see a dead branch:
- **Do NOT propose removing the guard or the branch.** (You don't propose fixes at all — Hard Rule 1.)
- Note it only if the dead-ness reflects a *genuine logic error the author did not intend* (e.g. the flag was meant to be set conditionally, or the wrong flag is tested). If the branch is simply gated-off intent with a comment explaining why, it is NOT a finder candidate — leave it.
- If you cannot tell intent from non-intent, that uncertainty means it is at best a `verify-bugs` question — raise it as a low-confidence observation, never as a confident defect.

### Triviality screen (drop harmless dead code)

Provably-dead code that changes nothing if left alone is noise, not a defect. Example: a redundant `if x is None:` that sits *after* an earlier `if x is None: return` — the second check is unreachable but harmless. Do NOT report these. A finder candidate must have a plausible *behavioral* consequence (wrong output, crash, silent no-op of intended logic), not merely "this line can't run."

## Finder Prompt Contract (Bake Into Every Finder)

Every finder agent prompt MUST state, verbatim in spirit:

1. **Scope:** "You may only read and report on these files: <list>. Do not range outside them."
2. **Whitelist:** "Report ONLY defects in these classes: <the list above>. Defensive guards against conditions that cannot occur are NOT bugs and must not be reported."
3. **No fixes, no grading, no success-claims:** "Do NOT propose any code change (no fix, no deletion, no rewrite). Do NOT label any finding REAL/confirmed/valid — not in the findings and not in any summary, wrap-up, or verdict block — and do NOT declare your run successful, complete, or ready. Verdicts belong to the verifier. End with the candidate list (or `NO FINDINGS`); do not append a confidence judgement on your own pass. You are listing suspicions to be adversarially tested, nothing stronger."
4. **Set-then-guard + triviality:** "Before reporting a dead branch, apply the Set-Then-Guard and Triviality rules: a provably-dead branch that is deliberate gated-off intent (especially one with an explaining comment) is NOT a defect; harmless dead code after an early return is NOT a defect."
5. **Zero is valid:** "If you find no qualifying defect, reply exactly `NO FINDINGS`. Finding nothing is a correct, complete answer. Do not invent issues to fill the report."
6. **Evidence per candidate:** "For each candidate give exact `file:line` (verify the path and line against the file you actually read — do not guess), quote the exact code, state the surrounding logic correctly, give the concrete reachable input/path that would trigger the defect, and state the behavioral consequence. No proposed fix."

## Procedure

### 1. Build The Partition
- Map the change set (or target area) to the subsystem list above.
- Produce one finder assignment per subsystem with an explicit file list.

### 2. Run Finders (Cheap Model, Parallel)
- Run finders in parallel; a small/cheap model is appropriate (the discovery pass that produced this methodology was ~80% Haiku).
- Collect each finder's candidates (or its `NO FINDINGS`).

### 3. Pre-Filter Obvious Quota-Filling And Self-Graded Claims
- Drop any candidate that is a guard against an impossible condition.
- Drop any candidate that proposes a deletion/fix (it violated the contract — re-read the code yourself before passing it on).
- Strip any "REAL/confirmed/valid/success/complete" language wherever it appears — including a finder's closing summary or sign-off; a finder cannot confer it. The verdict is assigned downstream by `verify-bugs`.

### 4. Hand Off To Verification
- Every surviving candidate goes to `verify-bugs`. **No candidate is accepted on the finder's word alone**, and a candidate that proposes deleting a dead-but-intentional branch must reach the verifier flagged as a possible HARMFUL.

## Reporting Format

Return, grouped by subsystem:
- Each candidate: `file:line`, quoted wrong code, the surrounding logic, trigger path, behavioral consequence — NO proposed fix, NO verdict word
- Per-subsystem `NO FINDINGS` where applicable (report it — it is a result)
- Counts: subsystems hunted, candidates raised, candidates pre-filtered as quota-filling or as fix/deletion-proposals
- Do NOT append a closing line that grades your own findings or declares the run complete/successful — the candidate list IS the deliverable.

## Pass Criteria

- Every finder was locked to one subsystem with an explicit file list
- Every finder prompt carried the whitelist, the two hard rules (no fixes, no self-grading/success-claims), the set-then-guard + triviality rules, and the zero-findings clause
- No candidate proposes a code change, and none is labeled REAL/confirmed by the finder — including in any summary or sign-off
- No accepted candidate is a defensive guard against an impossible condition, a deliberate gated-off branch, or harmless dead code
- All surviving candidates are queued for `verify-bugs` (none accepted unverified)
