AI-authored note:

## Description

The history size setting removes one entry too early. A capacity of 1 keeps nothing and the default 20 retains only 19 entries. Lowering the setting also fails to trim an already-populated history.

Evict oldest entries only while the count exceeds the configured limit. Zero still disables new history entries.

## Notes

No latent tensor processing or GPU inference is claimed.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Five tests exercise the real History and Item classes through the post-save image-result call shape, with Torch and startup imports stubbed. Baseline: 3 failures, 2 passes. Fix: all 5 pass, covering capacity 1, default 20, reduced/increased limits and disabled storage.

Run: `python test/test-history-capacity.py`.

Scoped Ruff, Pylint, and whitespace checks passed.
