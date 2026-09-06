AI-authored note:

## Description

`POST /sdapi/v1/prompt-enhance` silently randomizes a supplied `seed: 0` because `req.seed or -1` changes zero to the random-seed sentinel. This prevents repeatable requests with that valid seed.

Pass the request seed directly to `get_fixed_seed`, which already handles the default `-1` sentinel.

## Notes

Positive seeds and omitted/`-1` random-seed behavior are preserved. This concerns the prompt-enhancement endpoint; it is separate from the previously corrected generation seed-list filtering.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12, FastAPI 0.124.4 and httpx 0.28.1. The real HTTP route, request/response models, endpoint, and seed helper execute through TestClient. Only the enhancement model and unrelated application startup dependencies are stubbed; no LLM inference is claimed.

- Baseline: request seed zero reaches the enhancer and response as randomized seed `1234567` with test RNG pinned.
- Fix: zero reaches both unchanged; positive seed 42 and omitted/`-1` random behavior also pass.
- Scoped Ruff, Pylint, and whitespace checks passed.
- [Reproducible API contract harness](https://github.com/QualiaRain/sdnext/blob/codex/verified-pr-batch-20260906/test/test-api-contract-regressions.py) is retained separately from this small fix; it can target either source tree with `--repo`.
