AI-authored note:

# Seven verified SD.Next contributions

Prepared by OpenAI Codex for Jamie (`QualiaRain`) on 2026-09-06. Each production fix passed independent review by a separate Codex agent. The account owner's request was to make as many high-confidence pull requests as possible to Vladmandic's repository.

**Status: seven separate branches published; zero upstream pull requests opened.** GitHub rejected upstream creation with HTTP 403, `Resource not accessible by integration`. The current connector has a GitHub App installation on QualiaRain's account and cannot open upstream PRs. No fork-only PRs were substituted. This package allows the authorized local Claude Code/GitHub CLI environment to complete submission.

Verified upstream source: `vladmandic/sdnext:dev` at `ddec927c90021257ad7f46a044f2da0db9b17009`. Every production branch is exactly one commit ahead of that source, with only its listed fix and any associated regression tests. The API harness is retained on this combined evidence branch. This combined branch is for testing and handoff; submit the seven individual branches.

| Fix | Published source | Exact submission text |
|---|---|---|
| Filename template arguments | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/filename-pattern-arguments) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/filename-pattern-arguments?expand=1) | [PR description](prs/01-filename.md) |
| Inline choices in wildcard files | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/file-wildcard-inline-choices) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/file-wildcard-inline-choices?expand=1) | [PR description](prs/02-wildcard.md) |
| Preprocessing API response schema | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/preprocess-response-schema) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/preprocess-response-schema?expand=1) | [PR description](prs/03-preprocess.md) |
| Prompt-enhancement seed zero | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/prompt-enhance-zero-seed) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/prompt-enhance-zero-seed?expand=1) | [PR description](prs/04-promptseed.md) |
| Filename seed zero | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/filename-zero-seed) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/filename-zero-seed?expand=1) | [PR description](prs/05-fileseed.md) |
| Raw percent-bearing Gallery folder names | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/gallery-raw-folder-names) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/gallery-raw-folder-names?expand=1) | [PR description](prs/06-gallery.md) |
| Wildcard path boundaries | [Branch](https://github.com/QualiaRain/sdnext/tree/fix/wildcard-path-boundaries) · [Compare](https://github.com/vladmandic/sdnext/compare/dev...QualiaRain:sdnext:fix/wildcard-path-boundaries?expand=1) | [PR description](prs/07-wildcardpath.md) |

## Local Claude Code handoff

Use an isolated checkout of this branch, an activated Python environment, and the existing GitHub CLI user login for QualiaRain. No upstream administrator privileges are required for ordinary fork PR submission. Do not add credentials to this repository or alter the user's working SD.Next checkout.

```sh
git clone --depth 1 --single-branch --branch codex/verified-pr-batch-20260906 https://github.com/QualiaRain/sdnext.git sdnext-pr-batch-20260906
cd sdnext-pr-batch-20260906
# Activate the repository's Python environment, then:
python contribution-batch/submit.py --submit
```

The script uses standard-library Python and the existing `gh` executable. Without `--submit`, it performs read-only preflight. Submission checks the GitHub hostname and account, exact upstream and branch commits, changed-file lists, and saved description hashes. It skips any existing open or closed PR for the branch, checks again before each creation, and verifies the resulting head, target, title, and body. It does not merge PRs or request individual reviewers.

If dev or a branch changed, refresh and retest affected work before updating the manifest. If creation is forbidden, stop and report the provider error; do not redirect the PR to the fork. A rerun reports already-created PRs and only creates missing ones. The final local-agent report should contain actual upstream URLs and accurately distinguish opened, existing, and blocked PRs.

## Verification

The seven changes were also combined and tested together:

- 43 Python test cases plus 5 subtests passed across filename and wildcard regressions.
- Five API contract checks passed through real FastAPI registration and handlers: preprocessing HTTP 200 with valid PNG, and prompt enhancement seeds 0, 42, -1, and omitted.
- The Gallery regression passed against the real transpiled TypeScript module.
- Scoped Ruff and Pylint passed for the modified Python modules; the Gallery branch passed core ESLint, TypeScript checks, and the production build.
- All seven remote comparisons were read back and verified as one-commit changes with the intended filenames.

```sh
python -m pytest -q test/test-file-wildcards.py test/test-wildcard-paths.py test/test-namegen-patterns.py test/test-namegen-seed.py
python test/test-api-contract-regressions.py
node test/test-gallery-folders.mjs
```

The Python tests need pytest, Pillow, pytz, rich, FastAPI 0.124.4, httpx 0.28.1, pydantic, and piexif. The Gallery test needs the repository Node dependencies, including TypeScript. API tests stub model execution and unrelated startup dependencies; no GPU or LLM inference is claimed. Windows wildcard behavior uses explicit path/file-read simulation, not a Windows run. Braced wildcard alternatives now use the existing weighted parser, so a fixed seed can map to a different choice. Individual descriptions contain baseline failures, commands, and specific scope limits.

## Review record

The initial broad Gallery URL-encoding idea was rejected after source tracing showed encoded file listings. Only the verified raw folder-object defect remains. Wildcard subpath matching initially risked breaking nested directory references emitted by the UI; review caught this and the final fix preserves those references and exact-file precedence. Earlier maintainer feedback on false-positive reproduction inputs informed the checks throughout this batch.
