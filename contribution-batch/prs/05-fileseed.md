AI-authored note:

## Description

A valid image seed of zero is mishandled by `FilenameGenerator` twice: the constructor ignores an explicit zero and may substitute the first batch seed, and the `[seed]` replacement omits zero because of a truthiness check. In a batch with seeds `[123, 0]`, the second image can therefore be named with seed 123.

Accept explicit nonnegative seeds and emit zero in the filename token.

## Notes

The real save path passes each image's `p.seeds` value to the constructor. Missing or `-1` seeds retain the existing processing-object fallback, and a generator without a processing object retains its existing behavior.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Tests import the real filename generator with startup/settings dependencies stubbed. No model inference is required or claimed.

- Baseline: five failed assertions, including the mixed batch, a single zero seed, and three processing-object fallbacks.
- Fix: all five test methods pass, including subcases and fallback compatibility.
- Run: `python test/test-namegen-seed.py`.
- Scoped Ruff, Pylint, and whitespace checks passed. The isolated PR was also tested independently of the filename-token-arguments fix.
