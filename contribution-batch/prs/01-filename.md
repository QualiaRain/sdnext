AI-authored note:

## Description

Filename patterns such as `[datetime<%Y>]` and `[hasprompt<cat|dog><sun|moon>]` currently remain literal in saved filenames. `FilenameGenerator.apply` correctly parses their arguments, but then looks up the original token, including those arguments, in the replacement table.

Use the parsed token name for the lookup. Existing format, timezone, and prompt arguments then reach their intended handlers.

## Notes

One production line changes. Unknown patterns retain their original spelling and arguments; case-insensitive names and argument order are preserved.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Python 3.12. The regression imports the actual filename generator with application settings/startup dependencies stubbed; no model inference is required or claimed.

- Baseline: 5 failed, 2 passed.
- Fix: 7 passed, covering custom datetime format, timezone, uppercase token name, ordered prompt arguments, no-match fallback, plain seed expansion, and unknown tokens.
- Run: `python test/test-namegen-patterns.py` (requires the usual Pillow, pytz, and rich dependencies).
- Scoped Ruff, Pylint, and `git diff --check` passed.
