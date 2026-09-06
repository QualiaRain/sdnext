AI-authored note:

## Description

Replacing a model with a file whose modification time is older than the cached version returns the previous model's digest. A missing file can also reuse a cached digest.

Treat any changed modification time as a cache miss and reject missing files before lookup.

## Notes

Content replacements that preserve the exact modification timestamp remain outside scope. Startup and persistence dependencies are stubbed; hashing uses real file bytes.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. Five test methods exercise the real cache and SHA256 functions with temporary files, including older/newer timestamps, absent files, unchanged files, and actual digest recalculation. Baseline: 7 failing subcases across 3 methods. Fix: all 5 methods pass.

Run: `python test/test-hash-cache-mtime.py`.

Scoped Ruff, Pylint, and whitespace checks passed.
