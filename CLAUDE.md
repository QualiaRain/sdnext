# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SD.Next is an all-in-one WebUI for AI image and video generation built on Stable Diffusion and dozens of other diffusion model families. It is a Python backend (Torch for inference, FastAPI for API routes, Gradio for UI components) with a JavaScript/CSS frontend.

Detailed agent instructions already exist in this repo and take precedence for their areas:
- `.github/copilot-instructions.md` — general guidelines (also referenced by `AGENTS.md`)
- `.github/instructions/core.instructions.md` — Python core runtime, startup, model loading, API, device logic
- `.github/instructions/ui.instructions.md` — frontend JS/HTML/CSS, localization, modernui/kanvas extensions
- `.github/skills/README.md` — repo-local skills for recurring tasks (porting models/pipelines, debugging model loading, auditing API/schedulers/scripts, lint workflow, etc.). Check this index before starting model-integration or audit work.

## Commands

A Python `venv` must be active for all Python commands: `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows). Node >= 22 with `pnpm`/`npm` is used for JS tooling and script orchestration.

```bash
python launch.py --debug        # full startup (server at :7860)
python launch.py --debug --test # startup self-test without serving (also: npm run test)
npm run lint                    # full sequence: pre-commit, eslint (core/ui/kanvas), ruff, pylint
npm run ruff                    # ruff check
npm run pylint                  # pylint over *.py modules/ pipelines/ scripts/ extensions-builtin/
npm run eslint                  # eslint javascript/
npm run eslint-ui               # eslint for extensions-builtin/sdnext-modernui
npm run eslint-kanvas           # eslint for extensions-builtin/sdnext-kanvas
npm run format                  # pre-commit run --all-files (line endings, whitespace, json/yaml checks)
```

Lint individual files directly with `ruff check <file>` and `pylint <file>` (after activating venv). When fixing lint, follow the order in `.github/skills/fix-lint/SKILL.md` (pre-commit, eslint, ruff, pylint) and skip findings explicitly marked with `TODO`.

### Tests

There is no pytest suite. Tests are API smoke scripts in `test/` and `cli/` that run against a **live server** (start one first with `python launch.py`):

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
- `extensions-builtin/` holds bundled extensions, notably `sdnext-modernui` (the actual UI; has its own eslint setup) and `sdnext-kanvas`. User extensions load from `extensions/`. Base frontend JS lives in `javascript/`.
- UI strings/hints live in localization JSON in `html/locale_*.json` and `html/override_*.json`; keep user-facing text changes synchronized with locale resources (see `.github/instructions/hints.instructions.md`).

## Conventions

- **PRs target the `dev` branch**, never `master`. Do not include unrelated edits or submodule changes.
- Code style intentionally diverges from default linters: long lines are allowed (ruff line-length 250, E501/pylint line-too-long disabled), bare/broad excepts are tolerated, imports may be mid-file. Prefer matching nearby code over generic style rules — `pyproject.toml` is the authority for what's enforced.
- Many directories under `modules/`, `pipelines/`, and `scripts/` are vendored third-party code excluded from pylint/ty (see ignore lists in `pyproject.toml`); don't reformat or lint-fix them.
- Behavior is driven by `SD_*` environment variables (e.g. `SD_LOAD_DEBUG`, `SD_INSTALL_DEBUG`) — respect these instead of hardcoding platform/model assumptions. `npm run debug` lists known debug flags.
- Temporary scripts or markdown reports go in `tmp/`; reusable test scripts go in `test/`; follow existing CLI/API tool patterns in `cli/` when adding automation.
- Logging uses `from modules.logger import log` with f-string style `key=value` formatting.
