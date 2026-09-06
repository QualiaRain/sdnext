AI-authored note:

## Description

Fixes #4996. A wildcard-file line containing text such as `forest, {morning|evening}, {rainy|misty}` is currently split at every pipe, dropping parts of the prompt. Expand curly-brace choices with the existing prompt parser before applying the legacy bare-pipe selection.

## Notes

One production line changes. Nested and weighted choices reuse the existing parser. Unbraced file alternatives retain their existing handling. Braced file alternatives now use the weighted parser, so a particular seed may select a different alternative than the previous bare-pipe implementation.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. The regression exercises `StyleDatabase.apply_styles_to_prompts` with real wildcard files and the real filesystem scanner; application startup dependencies are stubbed. No model inference is required or claimed.

- Baseline: 3 failed, 6 passed.
- Fix: 9 passed, covering complete positive/negative prompt lines, nested weighted choices, nested files, existing line/pipe/comment behavior, repeatability, and random-state preservation.
- Run: `python -m pytest -q test/test-file-wildcards.py` (requires pytest).
- Scoped Ruff, Pylint, and `git diff --check` passed.
