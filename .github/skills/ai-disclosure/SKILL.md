# AI Disclosure Skill

Use when preparing any upstream-facing PR, issue, or comment on behalf of the
account owner. Governs attribution, disclosure wording, and pre-submission
workflow.

---

## Invariants (always binding)

- **Claude never impersonates the user.** Claude-authored analysis is attributed
  to Claude, never voiced as the user's own understanding.
- **AI-generated commits carry a trailer:**
  `Co-Authored-By: Claude <noreply@anthropic.com>`
- **Branches for upstream PRs are cut from upstream `dev`**, not this fork's
  `master`, so fork-local files never appear in upstream PR diffs.

---

## Standardized disclosure line

Every upstream PR body must open with this italic paragraph. Adjust only the
clause describing what Claude did and what the owner did — keep the structure
and attribution language identical.

```
*Disclosure: this PR was authored by Claude (Anthropic's coding agent), which
[what Claude did: found the bug / wrote the fix / wrote this description / etc.].
The account owner reviewed a plain-language explanation of the fix and chose to
submit.*
```

**Prior PRs using this wording:** vladmandic/sdnext #4903, #4904, #4905.

### Retroactive updates

If this disclosure wording is ever improved, ask Claude to retroactively edit
the disclosure paragraph on prior PR bodies and comments where it appears.
Paste the new wording and ask: "find and update the disclosure on prior PRs."
The goal is that improved transparency or phrasing applies to the full record,
not just new submissions.

---

## Understanding tiers

Calibrate the disclosure clause to what actually happened. Do not overstate.

| Tier | When to use | Example clause |
|---|---|---|
| Fully verified | Owner ran a live before/after and confirmed the behavioral change | "ran the live verification described in Testing below" |
| Inspection-only | Structural argument holds without running the code | "verifiable by inspection against current `dev`" |
| Relying on Claude | Owner understood the concept but didn't independently verify the mechanics | "reviewed a plain-language explanation of the fix" |

These can combine: e.g. "found the bug and wrote the fix and this description;
the account owner ran the live verification and chose to submit."

---

## Pre-submission checklist

1. Adversarial self-review: Claude re-reads the PR as a skeptical maintainer and
   flags anything that could embarrass the submitter or be factually wrong.
2. Guided walkthrough: Claude explains the bug and fix in plain language until
   the owner understands it.
3. Owner self-attestation: owner confirms they're comfortable submitting.
4. Confirm the branch was cut from upstream `dev`, not fork `master`.
5. Confirm no fork-local files (CLAUDE.md, this skill, etc.) are in the diff.
6. Confirm the commit carries the `Co-Authored-By` trailer.
