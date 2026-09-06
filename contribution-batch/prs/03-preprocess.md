AI-authored note:

## Description

A successful `POST /sdapi/v1/preprocess` currently fails response validation with HTTP 500. The registered `models.ResPreprocess` requires an `info` field, while the handler returns `process.ResPreprocess` with `model` and `image`.

Register the handler's actual response schema. This also fixes the OpenAPI response contract and preserves the image field expected by `cli/api-preprocess.py`.

## Notes

One route declaration changes; handler output and model execution are unchanged.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12, FastAPI 0.124.4 and httpx 0.28.1 (repository pins). Real API registration, schemas, handler, and PNG encode/decode are exercised through FastAPI TestClient. The processor and unrelated application startup dependencies are stubbed; no model inference is claimed.

- Baseline: successful processor output causes HTTP 500; schema requires `info`.
- Fix: HTTP 200 with `model` and a valid PNG preserving the input's 2×3 size and RGB pixels; schema lists `model`/`image`.
- Scoped Ruff, Pylint, and whitespace checks passed.
- [Reproducible API contract harness](https://github.com/QualiaRain/sdnext/blob/codex/verified-pr-batch-20260906/test/test-api-contract-regressions.py) is retained separately from this one-line fix; it can target either source tree with `--repo`.
