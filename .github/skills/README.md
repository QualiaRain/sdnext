# Repo Skills

This folder contains repo-local Copilot skills for recurring SD.Next tasks.

## Available Skills

- `port-model`
  File: `port-model/SKILL.md`
  Use when adding or porting a model family into SD.Next and Diffusers; invokes `port-pipeline` when no upstream implementation exists, and includes `TransformerSpec`/`native_spec` requirements for `generic.load_transformer`, explicit base-model dispatch through `load_diffuser_force`, conditional flow-sampler and VAE-family registry updates, and wiki updates for new base models.

- `port-pipeline`
  File: `port-pipeline/SKILL.md`
  Use when assessing and porting a custom pipeline implementation into a Diffusers pipeline class; requires a scope/complexity summary and user confirmation before implementation, and invokes `port-model` afterward to complete applicable SD.Next model integration.

- `debug-model`
  File: `debug-model/SKILL.md`
  Use when a new or existing SD.Next/Diffusers model integration fails during detect, load, prompt encode, sample, or output handling.

- `check-api`
  File: `check-api/SKILL.md`
  Use when auditing API endpoints in `modules/api/api.py` and delegated API modules for route parameter correctness plus request/response signature consistency.

- `check-schedulers`
  File: `check-schedulers/SKILL.md`
  Use when auditing scheduler registrations from `modules/sd_samplers_diffusers.py` to verify class loadability, config validity against scheduler capabilities, and `SamplerData` correctness.

- `check-models`
  File: `check-models/SKILL.md`
  Use when running an end-to-end model integration audit covering loaders, detect/routing parity, reference catalogs, and custom pipeline API contracts.

- `check-processing`
  File: `check-processing/SKILL.md`
  Use when validating txt2img/img2img/control processing workflows from UI submit definitions to backend execution with parameter, type, and initialization checks.

- `check-ui`
  File: `check-ui/SKILL.md`
  Use when auditing Python-to-JavaScript UI bindings for Gradio `_js` callbacks, verifying `window` exposure and `ui/globals.d.ts` registration.

- `check-paths`  
  File: `check-paths/SKILL.md`  
  Use when auditing model-loading calls to verify `cache_dir` routing for `from_pretrained` and `from_single_file`.

- `check-scripts`
  File: `check-scripts/SKILL.md`
  Use when auditing `scripts/*.py` for correct Script overrides (`__init__`, `title`, `show`) and verifying `ui()` output compatibility with `run()` or `process()` parameters.

- `github-issues`
  File: `github-issues/SKILL.md`
  Use when reading SD.Next GitHub issues with `[Issues]` in title and producing a markdown summary with status and suggested next steps for each issue.

- `github-features`
  File: `github-features/SKILL.md`
  Use when reading SD.Next GitHub issues with `[Feature]` in title and producing a markdown summary with status and suggested next steps for each issue.

- `analyze-model`
  File: `analyze-model/SKILL.md`
  Use when analyzing an external model URL to classify implementation style and estimate SD.Next porting difficulty before coding.

- `diffusers-code`
  File: `diffusers-code/SKILL.md`
  Use when creating or editing code to be compliant with Hugging Face diffusers conventions, including PR-ready change preparation for diffusers.

- `reference-catalog`
  File: `reference-catalog/SKILL.md`
  Use when maintaining and validating model reference catalogs in `data/reference*.json`, including duplicate checks, thumbnail alignment, and checking every `reference-base` entry against `wiki/Model-Support.md` and `wiki/Models.md`.

- `fix-lint`
  File: `fix-lint/SKILL.md`
  Use when running the full lint workflow in strict order and fixing issues as needed (`pre-commit`, `eslint`, `ruff`, `pylint`), while ignoring findings explicitly marked with `TODO`.

- `todo`
  File: `todo/SKILL.md`
  Use when scanning the full codebase for `TODO` markers and producing a markdown document with proposed next steps for each item.

- `update-docs`
  File: `update-docs/SKILL.md`
  Use when reading markdown files from `wiki/` to correct markdown syntax, improve readability, and optionally normalize structure/links while preserving technical meaning.

- `update-hints`
  File: `update-hints/SKILL.md`
  Use when scanning `modules/ui*.py`, `scripts/*.py`, and `ui/locale/locale_en.json` to create missing hints, detect duplicates, flag incorrect hints without auto-updating them, and generate a categorized audit report.

- `sync-upstream`
  File: `sync-upstream/SKILL.md`
  Use when updating this fork from upstream `vladmandic/sdnext`: fetch and merge `master` (or `dev` on request), keep fork-local files, restore submodule pins instead of committing installer drift, verify startup, refresh fork-local guidance, and push to the working branch.

- `perf-sandbox`
  File: `perf-sandbox/SKILL.md`
  Use when running SD.Next for measurements or patch tests: isolated git worktrees with their own submodules (`scripts/mkwt.sh`), one server per port (`scripts/run-app.sh`, `scripts/stop-app.sh`), an offline tiny test model (`scripts/make_tiny_sd.py`), and a bit-exact end-to-end generation check (`scripts/e2e.py`).

- `perf-audit`
  File: `perf-audit/SKILL.md`
  Use when looking for performance problems: per-area measurement recipes, rules for measuring on a noisy machine, the finding format, and `workflow.js`, which runs one finder agent per subsystem.

- `perf-patch`
  File: `perf-patch/SKILL.md`
  Use when turning a performance finding into a verified patch: builder protocol (reproduce, minimal patch, prove gain and equivalence) and reviewer protocol (try to break it), with `workflow.js` running both for groups of candidates.

- `perf-land`
  File: `perf-land/SKILL.md`
  Use when applying reviewed performance patches as atomic commits: apply order, UI rebuild, lint, combined verification with the end-to-end check, commit messages, push, and reporting held or rejected candidates.

## Notes

- Keep skills narrowly task-oriented and reusable.
- Prefer referencing existing repo patterns over generic framework advice.
- Update this index when adding new repo-local skills.
