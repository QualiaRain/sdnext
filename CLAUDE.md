# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SD.Next is an all-in-one WebUI for AI image and video generation built on Stable Diffusion and dozens of other diffusion model families. It is a Python backend (Torch for inference, FastAPI for API routes, Gradio for UI components) with a TypeScript/CSS frontend.

Detailed agent instructions already exist in this repo and take precedence for their areas:
- `.github/copilot-instructions.md` — general guidelines (also referenced by `AGENTS.md`)
- `.github/instructions/core.instructions.md` — Python core runtime, startup, model loading, API, device logic
- `.github/instructions/ui.instructions.md` — frontend TypeScript/HTML/CSS, build and lint commands, localization, modernui/kanvas extensions
- `.github/instructions/hints.instructions.md` — typography rules for hint text in `ui/locale/locale_en.json`
- `.github/skills/README.md` — repo-local skills for recurring tasks (porting models/pipelines, debugging model loading, auditing API/schedulers/scripts, lint workflow, etc.). Check this index before starting model-integration or audit work.

## Commands

A Python `venv` must be active for all Python commands: `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows). Node >= 24 with `pnpm` (version pinned by `packageManager` in `package.json`) is used for JS tooling and script orchestration; `npm run <script>` works for the same scripts.

```bash
python launch.py                # full startup (server at :7860); debug logging is on by default, SD_NODEBUG=1 turns it off
python launch.py --test         # startup self-test without serving (also: npm run test)
npm run lint                    # full sequence: pre-commit, eslint, tsc, ruff, pylint
npm run full                    # lint plus codespell, ty and pyright
npm run ruff                    # ruff check
npm run pylint                  # pylint over *.py modules pipelines scripts extensions-builtin
npm run eslint                  # eslint for core ui/, modernui and kanvas (eslint:core, eslint:modernui, eslint:kanvas)
npm run tsc                     # TypeScript type check (tsc:core, tsc:modernui, tsc:kanvas)
npm run build                   # rebuild UI bundles (build:core -> ui/dist/, build:modernui, build:kanvas)
npm run precommit               # pre-commit run --all-files (line endings, whitespace, json/yaml checks)
npm run pyright                 # pyright type check (alternative: npm run ty)
npm run codespell               # spelling check
npm run compile                 # python test/test-compile.py
npm run todo                    # list TODO markers in *.py modules/ pipelines/
```

Lint individual files directly with `ruff check <file>` and `pylint <file>` (after activating venv). When fixing lint, follow the order in `.github/skills/fix-lint/SKILL.md` (pre-commit, eslint, ruff, pylint) and skip findings explicitly marked with `TODO`.

### Tests

There is no pytest suite. Tests are plain scripts in `test/` and `cli/` of two kinds.

Offline scripts state "No running server required" in their docstring and run directly:

```bash
python test/test-json-helpers.py          # one offline script
python test/test-prompt-curly-braces.py
```

API smoke scripts run against a **live server** with a model loaded (start one first with `python launch.py`):

```bash
./test/full-test.sh                                   # full API smoke suite
python cli/api-txt2img.py --prompt "test" --steps 10  # single API test
python test/test-generation-api.py                    # individual test scripts
```

`installer.py` handles dependency installation and environment setup automatically during launch; don't pip-install project dependencies manually.

## Architecture

### Startup flow

`webui.sh`/`webui.bat` → `launch.py` (arg parsing, installer) → `installer.py` (dependency/environment setup) → `webui.py` (server + UI init) → `modules/`. Initialization order and import timing in `launch.py`/`webui.py` are deliberate and fragile — do not move initialization steps unless required, and preserve partial-failure tolerance and logging in parallel scans and extension loading.

### Core runtime

- `modules/shared.py` is the single source of truth for global runtime state: `shared.opts` (options), loaded model references, backend/device flags. Avoid introducing new cross-module mutable globals.
- `modules/devices.py` and related modules handle device/backend abstraction. Code must stay platform-neutral across CUDA/ROCm/IPEX/DirectML/OpenVINO/MPS — never assume CUDA-only behavior.
- `modules/processing*.py` implement the generation workflow: `processing.py` (entry), `processing_class.py` (StableDiffusionProcessing classes), `processing_diffusers.py` (Diffusers execution), plus args/callbacks/correction/VAE/video stages.
- `modules/api/` contains FastAPI routes (`api.py`, `endpoints.py`, etc.); reuse the shared queue/state helpers there rather than ad-hoc request handling.

### Model loading

- `modules/sd_detect.py` guesses model type from file size/name/metadata and maps it to a pipeline via `modules/shared_items.get_pipelines()`.
- `modules/sd_models.py` orchestrates loading and dispatches to per-family loaders in `pipelines/model_*.py` (e.g. `pipelines/model_flux.py`), which select Diffusers pipeline classes and apply quantization/offload via `modules/model_quant.py` and `modules/sd_offload.py`.
- Samplers/schedulers are registered in `modules/sd_samplers_diffusers.py`.
- When adding a model family, use the `port-model` / `port-pipeline` skills as the playbook and reuse `pipelines/generic.py` patterns instead of creating parallel abstractions.

### Scripts and extensions

- `scripts/*.py` are dynamically loaded plug-ins subclassing `Script` from `modules/scripts_manager.py` (key overrides: `title`, `show`, `ui`, then `run` or `process`). `ui()` outputs must match `run()`/`process()` parameters.
- `extensions-builtin/` holds bundled extensions as git submodules, notably `sdnext-modernui` (the actual UI; has its own eslint/tsc/build setup) and `sdnext-kanvas`. User extensions load from `extensions/`; do not inspect or modify files there unless asked.
- The core frontend is TypeScript in `ui/*.ts`, bundled by `npm run build:core` into `ui/dist/sdnext.mjs`. Never edit built output (`ui/dist/`, `extensions-builtin/*/javascript/`); change the source and rebuild. Styles are in `ui/css/`, static assets in `ui/assets/`.
- UI strings/hints live in `ui/locale/locale_en.json`; add or change user-facing text there (see `.github/instructions/hints.instructions.md`). The other `ui/locale/locale_*.json` files are generated translations and `override_*.json` are manual overrides: do not edit either. Locale tooling: `npm run localize` (`test/localize.mjs`).

## Conventions

- **PRs target the `dev` branch**, never `master`. Do not include unrelated edits or submodule changes.
- Code style intentionally diverges from default linters: long lines are allowed (ruff line-length 250, E501/pylint line-too-long disabled), bare/broad excepts are tolerated, imports may be mid-file. Prefer matching nearby code over generic style rules — `pyproject.toml` is the authority for what's enforced.
- Many directories under `modules/`, `pipelines/`, and `scripts/` are vendored third-party code excluded from pylint/ty (see ignore lists in `pyproject.toml`); don't reformat or lint-fix them.
- Behavior is driven by `SD_*` environment variables (e.g. `SD_LOAD_DEBUG`, `SD_INSTALL_DEBUG`) — respect these instead of hardcoding platform/model assumptions. `npm run debug` lists known debug flags.
- Temporary scripts or markdown reports go in `tmp/`; reusable test scripts go in `test/`; follow existing CLI/API tool patterns in `cli/` when adding automation.
- Logging uses `from modules.logger import log` with f-string style `key=value` formatting.
- Project documentation markdown lives in the `wiki/` submodule (see the `update-docs` skill; developer guidelines are `wiki/Dev-*.md`, indexed in `wiki/Dev-Home.md`); model reference catalogs live in `data/reference-*.json` (see the `reference-catalog` skill).

## Responsible AI Disclosure

This fork prepares AI-assisted contributions to the upstream project. The following invariants are always binding; the full policy lives in `.github/skills/ai-disclosure/SKILL.md`, which **MUST be read in full before preparing or posting any upstream-facing PR, issue, or comment**.

- **Claude never impersonates the user.** Claude-authored analysis in any upstream-facing text is explicitly attributed to Claude, never voiced as the user's own understanding.
- **Every upstream PR/issue discloses an understanding tier** (fully / partially / lightly reviewed) per the skill's verbatim wording, and nothing goes upstream until the skill's mandatory workflow (adversarial self-review → guided walkthrough → user self-attestation) is complete and the user has approved the final text.
- **AI-generated commits on this fork carry a `Co-Authored-By: Claude <noreply@anthropic.com>` trailer.**
- **Branches intended for upstream PRs are cut from upstream `dev`**, not this fork's `master`, so fork-local files (this one included) never ride along in PR diffs.
