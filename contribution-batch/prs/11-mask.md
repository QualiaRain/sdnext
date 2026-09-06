AI-authored note:

## Description

The bundled cli/api-mask.py never sends a model field, but ReqMask declares nullable mask/model fields without defaults. Pydantic 2 consequently requires them and rejects the client request with HTTP 422.

Give both optional fields an explicit None default; keep image and type required.

## Notes

Segmentation inference and unrelated startup dependencies are stubbed; no model download or inference is claimed.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Five tests use real FastAPI/Pydantic request validation, APIProcess.post_mask, and PNG encoding. Baseline: 3 failures, 2 passes. Fix: all 5 pass, including the exact built-in client payload, omitted optional fields, explicit model/mask, required fields, and OpenAPI.

Run: `python test/test-mask-request-defaults.py`.

Scoped Ruff, Pylint, and whitespace checks passed.
