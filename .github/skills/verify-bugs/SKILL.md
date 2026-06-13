---
name: verify-bugs
description: "Adversarially verify each claimed bug against current dev before it touches a PR: assign a REAL/WEAK/BOGUS/STALE/HARMFUL verdict with reproduction-level evidence, and screen every proposed fix for regressions. Pairs with find-bugs."
argument-hint: "Pass the claim list (or a finder report) to verify; optionally the dev ref to verify against"
---

# Verify Bugs (Adversarial Verifier Pass)

Independently re-prove or reject every claimed defect against **current `dev`** before any fix is written or submitted. This is the gate that keeps quota-filling, stale claims, and regression-fixes out of the repo. Pairs with `find-bugs`.

## When To Use

- A `find-bugs` finder pass produced candidates that need acceptance
- An external/cloud agent returned a batch of claimed fixes ("~N bugs found") that must be vetted before a PR
- You are triaging an unverified fix branch against the live tree

## Guidance

- Consult `.github/instructions/core.instructions.md` for relevant core runtime guidance before proceeding.

## Verifier Stance: Adversarial, Independent, Current-Dev

The verifier's job is to **try to break each claim**, not confirm it:

- **Independent:** do not trust the finder's reasoning. Re-read the actual code on current `dev` and re-derive whether the defect is real. A finder's confident write-up is not evidence — and a finder is forbidden from grading its own claim, so any "REAL/confirmed/success" language attached to an incoming claim or its summary carries zero weight.
- **Against current dev:** the claim may have been written against an older tree. Verify on the live `dev` ref — a real-looking bug may already be fixed (STALE) or the surrounding code may have moved.
- **Reachability-first:** a defect is only REAL if a reachable input/call path actually triggers it. "This looks unsafe in isolation" is not enough — show the path, or downgrade.
- **Dead-but-intentional is not REAL:** a branch can be provably unreachable yet deliberately gated-off intent (a comment usually gives it away). Unreachable-by-design is BOGUS as a defect; only flag it if the dead-ness reflects a genuine logic error (wrong flag set, wrong flag tested). See the Set-Then-Guard note in `find-bugs`.
- **Catch active regressions:** some "fixes" make things worse (e.g. swapping threaded settings-save for a blocking one; or "removing a dead guard" so an img2img-only code path runs on txt2img and hits an `AttributeError`). Flag these loudly — they are more dangerous than a bogus no-op claim.

## Verdict Taxonomy

Assign exactly one verdict per claim:

- **REAL** — confirmed defect on current `dev` with a reachable trigger path AND a non-trivial behavioral consequence. Accept; proceed to fix.
- **WEAK** — plausible but the trigger path is unproven, the impact is negligible/trivial (e.g. provably-dead-but-harmless code, like a redundant `is None` check after an early return), or it depends on an input the code never receives. Do not submit; note why.
- **BOGUS** — not a defect. Most commonly a defensive guard against a condition that cannot occur (e.g. `str.split()` returning `[]`, a `None` that is never `None` on that path), or a dead branch that is deliberate gated-off intent. Reject.
- **STALE** — was real on some older tree but is already fixed or no longer applicable on current `dev`. Reject.
- **HARMFUL** — the claim's *proposed change* would regress behavior (correctness, concurrency, performance) — including "delete this dead branch" when the branch is intentional. Reject and flag prominently; never let it ride along in a batch.

Only **REAL** claims advance to a fix/PR.

## Procedure

### 1. Resolve The Verification Base
- Confirm the current `dev` ref. Verify every claim against it, not against the branch the claim was authored on.

### 2. Re-Derive Each Claim Independently
For each claim:
- Open the cited `file:line` on current `dev`. **Re-confirm the path and line number yourself** — finders sometimes cite the wrong file or line.
- Re-read the surrounding logic without relying on the finder's explanation.
- Establish whether the asserted defect is actually present.

### 3. Prove Reachability And Non-Triviality
- Identify a concrete input or call path that triggers the defect.
- If none exists (the bad branch is unreachable, the value is never the problematic type), downgrade to WEAK or BOGUS.
- If reachable but the consequence is nil (harmless dead code), downgrade to WEAK.

### 4. Check For Already-Fixed / Moved Code
- If the defect is absent on current `dev` (fixed, refactored away), mark STALE.

### 5. Intent + Regression Screen
- For a dead-branch claim, decide intent: is this a logic error, or a deliberate gated-off branch (comment, paired flag)? Deliberate → BOGUS.
- For each claim that proposes a fix, check the fix does not change working behavior (threading, concurrency, perf, output) and does not delete intentional code. If it does, mark HARMFUL.

### 6. Parallelize Across Slices (Optional)
- For a large batch, split claims across several verifier agents by file/subsystem slice; a capable model is appropriate here (the reference run used Sonnet verifiers over Haiku-found claims). Verifiers work independently.

## Reporting Format

Return a table, one row per claim:
- claim id / source (finder + subsystem, or branch)
- file:line (as re-confirmed on current `dev`)
- verdict (REAL | WEAK | BOGUS | STALE | HARMFUL)
- evidence (the reachable trigger path + consequence for REAL; the reason for rejection otherwise)
- minimal fix (REAL only)

Then summary counts: REAL / WEAK / BOGUS / STALE, plus any HARMFUL called out separately at the top.

## Pass Criteria

- Every claim verified against current `dev`, re-derived independently of the finder, with file:line re-confirmed
- Every REAL verdict carries a reachable trigger path AND a non-trivial consequence (not "looks unsafe", not harmless dead code)
- Every BOGUS/STALE carries the reason it was rejected; dead-but-intentional branches are BOGUS, not REAL
- Any HARMFUL claim — including "delete this dead/intentional branch" fixes — is flagged prominently and excluded from the fix set
- Only REAL claims are forwarded to a fix/PR
