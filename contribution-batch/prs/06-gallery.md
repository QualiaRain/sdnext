AI-authored note:

## Description

`/browser/folders` returns raw `{path, label}` objects. `GalleryFolder` incorrectly URI-decodes those values: a configured folder such as `outputs/100% complete` throws `URIError`, and a literal `%20` in a path silently becomes a space.

Preserve the raw object fields. The older encoded-string response path still uses its existing decoder.

## Notes

Two TypeScript lines change. The required core bundle and source map are rebuilt. This addresses raw folder-object handling only.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux and Node.js. The regression executes the actual transpiled gallery module with minimal DOM startup stubs.

- Baseline: construction from the backend-shaped percent-bearing folder object throws `URIError`.
- Fix: raw percent and literal `%20` paths/labels, Windows-style paths, label fallback, and legacy encoded strings pass.
- Run: `node test/test-gallery-folders.mjs` after installing the repository's Node dependencies.
- `pnpm run eslint:core`, `pnpm run tsc:core`, `pnpm run build:core`, and whitespace checks passed.
- No browser visual or GPU inference test is claimed.
