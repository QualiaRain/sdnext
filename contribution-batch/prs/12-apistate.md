AI-authored note:

## Description

Exceptions in preprocessing, masking, or object detection return HTTP 500 while leaving the shared job state marked running with its API flag set.

Pair each started job with state.end in a finally block, following the existing detail endpoint's pattern. Exception responses, queue ordering, and model operations retain their current behavior.

## Notes

Model inference and unrelated startup dependencies are stubbed. No concurrency-policy changes or GPU inference are claimed.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Seven test methods exercise real FastAPI handlers, image encoding, and shared_state.State. Baseline: 5 failures, 2 passes. Fix: all 7 pass, including model-boundary errors, actual Pillow encoding errors, successful requests, and empty mask results.

Run: `python test/test-processing-state-cleanup.py`.

Scoped Ruff, Pylint, and whitespace checks passed.
