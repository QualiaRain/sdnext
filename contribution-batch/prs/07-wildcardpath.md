AI-authored note:

## Description

An explicit wildcard reference such as `__nsp/color__` can select `othernsp/color.txt` or `nsp/color-extra.txt` because the subpath lookup uses a substring match. Which wrong file wins depends on the scan order.

Match complete path components while preserving the existing exact-file-first lookup and directory fallback.

## Notes

Nested directory references emitted by the Wildcards UI remain supported, including references without a trailing slash. Basename references, absolute paths, and mixed separators remain supported.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Tests run the real wildcard loader and filesystem scanner with temporary files. Windows path matching uses explicit `ntpath` and file-read simulation; execution on Windows is not claimed. Application startup dependencies are stubbed; no model inference is required.

- Baseline: 7 failed, 15 passed.
- Fix: 22 passed, including near-match collisions, exact-file precedence, nested directory references, basename/absolute paths, and mixed separators.
- Run: `python -m pytest -q test/test-wildcard-paths.py` (requires pytest).
- Scoped Ruff, Pylint, and whitespace checks passed.
