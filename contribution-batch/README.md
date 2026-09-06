AI-authored note:

# Six additional SD.Next fixes; thirteen prepared contributions

Prepared by OpenAI Codex for Jamie (`QualiaRain`) on 2026-09-06 after a second bounded inspection. Each new defect was reproduced, fixed, and approved by a separate Codex reviewer. Current upstream dev remains `ddec927c90021257ad7f46a044f2da0db9b17009`.

**Status: thirteen individual branches published across both batches; zero upstream PRs opened.** The connector still lacks permission to open PRs in Vlad's repository. This package retains the first seven submission entries and adds the six below, so the local submission script can handle all thirteen.

| New improvement | Verified user impact | Prepared contribution |
|---|---|---|
| History capacity | A limit of 1 discards every entry; default 20 keeps only 19. Lowered limits also fail to trim existing entries. | [Source](https://github.com/QualiaRain/sdnext/tree/fix/history-capacity) · [PR text](prs/08-history.md) |
| Masking API compatibility | The bundled masking client is rejected with HTTP 422 because optional fields have no defaults. | [Source](https://github.com/QualiaRain/sdnext/tree/fix/mask-request-defaults) · [PR text](prs/11-mask.md) |
| Extension Update action | The Update button changes its label but never clicks the backend control. | [Source](https://github.com/QualiaRain/sdnext/tree/fix/extension-update-dispatch) · [PR text](prs/13-extension.md) |
| Model hash cache | Replacing a model with an older-timestamp file can reuse the old model's digest; missing files can reuse cached digests too. | [Source](https://github.com/QualiaRain/sdnext/tree/fix/hash-cache-mtime-changes) · [PR text](prs/09-hash.md) |
| Seed-zero prompt reproducibility | Seed 0 produces varying curly choices and wildcards despite a fixed generation seed. | [Source](https://github.com/QualiaRain/sdnext/tree/fix/styles-zero-seed) · [PR text](prs/10-styleszero.md) |
| API failure cleanup | Failed preprocess, mask, and detection requests can leave the app reporting a running API job. | [Source](https://github.com/QualiaRain/sdnext/tree/fix/api-processing-state-cleanup) · [PR text](prs/12-apistate.md) |

The first seven fixes and their evidence remain in the [first batch](https://github.com/QualiaRain/sdnext/tree/codex/verified-pr-batch-20260906/contribution-batch). Their exact PR descriptions are also retained in this package. This branch combines only the six new fixes for integration testing; the submission script uses all thirteen separate branches listed in `manifest.json`. Do not open a combined upstream PR from this evidence branch.

## Submit through the existing local GitHub login

Use a new isolated checkout, Python 3.10+ with the repository's environment activated, and `gh` already authenticated as QualiaRain. The script uses only the Python standard library and the existing CLI credentials.

```sh
git clone --depth 1 --single-branch --branch codex/verified-pr-batch2-20260906 https://github.com/QualiaRain/sdnext.git sdnext-pr-batch2-20260906
cd sdnext-pr-batch2-20260906
# Activate the repository's Python environment, then:
python contribution-batch/submit.py --submit
```

Without `--submit`, the script performs read-only preflight. The unchanged, independently reviewed submission script pins github.com and the upstream target, checks exact source commits and description hashes, skips existing open or closed PRs, rechecks before each write, and verifies the resulting PR payload. It does not merge anything. If upstream dev changed, refresh and retest affected work before updating the manifest. If provider access is denied, stop and report the error; do not redirect submissions to the fork.

The two UI fixes have independently rebuilt assets. Once either UI contribution lands, regenerate the other branch's generated assets if necessary to resolve source-map conflicts. Report actual opened/existing/blocked upstream PR URLs after submission.

## Verification

All six new changes were applied together without source conflicts. The combined tree passed **30 Python test methods/cases and the extension-button regression**, plus scoped Ruff/Pylint and whitespace checks. The UI branch passed core ESLint, TypeScript checks, and production build.

| Regression | Baseline | Fixed |
|---|---|---|
| History capacity | 3 failures, 2 passes | 5 passes |
| Mask request defaults | 3 failures, 2 passes | 5 passes |
| Hash cache | 7 failing subcases across 3 methods | 5 methods pass |
| Seed-zero prompt expansion | 4 failures, 4 passes | 8 passes |
| API processing state | 5 failures, 2 passes | 7 methods pass |
| Extension update | Path changes; backend click absent | Input updates before exactly one click |

```sh
python test/test-history-capacity.py
python test/test-hash-cache-mtime.py
python -m pytest -q test/test-styles-seed-zero.py
python test/test-mask-request-defaults.py
python test/test-processing-state-cleanup.py
node test/test-extension-update.mjs
```

Python dependencies include pytest, Pillow, rich, FastAPI 0.124.4, httpx 0.28.1, pydantic, and piexif; Node tests use the repository's TypeScript dependency. Model inference and unrelated startup dependencies are stubbed. Actual API validation, handler logic, PNG encoding, shared job State, filesystem hashing, prompt expansion, and UI dispatch execute. No live model/GPU run, browser visual test, or extension download is claimed.

Hash replacements retaining the identical modification timestamp remain outside scope. A suspected nested-directory refresh defect was not promoted because current callers force reload, preventing demonstrated user impact. Source-map build-path noise was removed before the UI fix passed review. All six published branch comparisons were read back and verified as exactly one commit with the intended files.
