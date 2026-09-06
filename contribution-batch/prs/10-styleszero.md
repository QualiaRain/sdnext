AI-authored note:

## Description

A valid generation seed of 0 is treated as unseeded while expanding curly choices, style wildcards, and file wildcards. Repeated generations with seed 0 can therefore use different prompt text despite a fixed image seed.

Use the same seeded path for all nonnegative seeds. The -1 random sentinel keeps its existing behavior.

## Notes

Application startup dependencies are stubbed. No GPU inference is required or claimed. This is distinct from prompt-enhancement API and filename seed handling.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Eight tests cover the real StyleDatabase.apply_styles_to_prompts generation entry point, positive/negative prompts, real wildcard files, mixed 0/123/0 batches, helper calls, -1 behavior, and random-state restoration. Baseline: 4 failures, 4 passes. Fix: all 8 pass.

Run: `python -m pytest -q test/test-styles-seed-zero.py`.

Scoped Ruff, Pylint, and whitespace checks passed.
