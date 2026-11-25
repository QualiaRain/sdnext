---
name: perf-audit
description: "Find and size real performance problems in SD.Next with evidence: per-area measurement recipes (startup, installer, imports, UI build, page load, API, generation, memory, browser), rules for measuring on a noisy machine, a finding format, and a Workflow script that runs one finder per subsystem."
argument-hint: "Optionally name the areas to audit (installer, startup-imports, ui-build, frontend, discovery, model-load, processing, prompts-lora, images-io, api, features); default is all"
---

# Performance Audit

Locate optimization opportunities that are real, material and fixable with a narrow, behavior-preserving change, and record each one in a form that `perf-patch` can act on.

## When To Use

- The user asks to optimize SD.Next, or to find out why something is slow
- Before choosing what to change: measure first, then pick
- After an upstream sync, to see whether earlier findings still apply

## Guidance

- Read `.github/copilot-instructions.md` and `.github/instructions/core.instructions.md` first: startup import and init order in `launch.py` and `webui.py` is deliberate and must not be reordered.
- Use the `perf-sandbox` skill to run servers. Put scratch scripts and data in `tmp/` (gitignored), for example `tmp/agents/<area>/`.

## What Counts As A Finding

- Real: the code runs in normal use. Show the call path and how often it runs (every launch, generation, sampling step, poll, page load, or per model, LoRA, image or extension).
- Material: a user would notice it, or it compounds. Weigh by what real users have: a GPU, thousands of models, LoRAs and embeddings, tens of thousands of output images, several extensions, servers that stay up for days.
- Safe: a narrow change exists that keeps outputs, API payloads, option names and defaults, UI behavior and startup order unchanged. Changes in behavior are allowed only as an explicit decision for the user.
- Out of scope: vendored code (`main.ignore-paths` in `pyproject.toml`), submodules (`extensions-builtin/*`, `wiki`), built output (`ui/dist`), kernels and numerics.
- Check `git show upstream/dev:<path>` for every finding: upstream may already have changed or fixed it.

## Measuring On A Noisy Machine

- Interleave runs (before, after, before, after) with at least five pairs and report minimum and median for each side. Report the load (`uptime`) next to wall-clock numbers.
- Prefer measures that do not depend on load: CPU time, call counts, bytes, object counts, number of subprocesses or network requests, event-loop stall.
- In torch micro-benchmarks call `torch.set_num_threads(1)` to avoid thread oversubscription on a shared machine.
- Keep benchmarks short and in-process where possible (before and after in the same process, best of N). The offline scripts in `test/` (docstring "No running server required") show how to import app modules without a server.
- Mark anything you could not measure as an estimate and give the reasoning.

## Recipes By Area

| Area | How to measure | What to read |
|---|---|---|
| Whole launch | `run-app.sh` then the log | `Startup time`, `Installer time`, timestamps per phase |
| Phase profile | `python launch.py --test --profile --port <free>` | per-phase top functions (Torch, Requirements, Submodule, Extensions, Preload, WebUI) |
| Imports | `python -X importtime launch.py --test --port <free> 2> importtime.raw` | columns: self us, cumulative us, indented module; children print before their parent |
| Full profile | `python -m cProfile -o launch.prof launch.py --test --port <free>` | `pstats.Stats('launch.prof').sort_stats('cumulative').print_stats(40)` |
| Installer paths | delete `data/installer.json` to force the full path | log lines `State: cached=` and `Startup: launch=quick` or `full` |
| Page load | `curl -s -o /dev/null -w '%{size_download} %{time_total}\n' [-H 'Accept-Encoding: gzip'] http://127.0.0.1:<port>/` and the same for `/config` and `/info` | size and server time; break `/config` down by component type and `elem_id` to see what dominates |
| API latency | loop over GET endpoints, median of several calls each | slow or oversized endpoints, and which ones the UI polls (`ui/*.ts`) |
| Event loop | time a trivial endpoint (for example `/sdapi/v1/motd`) while load runs | added latency means blocking work inside an `async def` handler or middleware |
| Generation | `perf-sandbox/scripts/e2e.py`, and `py-spy record -p <pid> -r 250 --format raw -o out.raw` during it | per-generation timers in the log; collapsed stacks show where wall time goes |
| GC and memory | log lines `GC: ... time=`; `VmRSS` in `/proc/<pid>/status`; `len(gc.get_objects())` in-process | repeat 30 generations or several model switches and compare growth |
| Browser | Playwright with Chromium: navigation timing, request count and bytes, long tasks, DOM node count, CDP `Performance.getMetrics` while idle | cost that grows with cards, gallery files or dataset size |

Browser work on a shared machine:

- Try a UI change without rebuilding: rewrite exact strings of `ui/dist/sdnext.mjs` in the test script and serve the result with Playwright's `page.route`; rebuild with `pnpm run build:core` only for the final check.
- Before trusting a DOM equivalence check, compare the original with itself; timestamps and image titles that change when lazy images finish loading differ between runs.
- Chromium renderers crash ("Target crashed") when less than about 4 GB is free: wait for `MemAvailable` in `/proc/meminfo` before each run and run one browser at a time.

Build synthetic libraries instead of downloading: thousands of tiny `.safetensors` files with metadata headers plus `.json` and preview sidecars, or an output folder with 20,000 small images, all under `tmp/`, passed to the server with `--lora-dir`, `--data-dir` or `--models-dir`.

## Finding Format

Save each finding as one JSON file (for example `tmp/perf/findings/<area>-<n>.json`) with these fields: `id`, `title`, `files` (path:line), `category` (startup, page-load, request, generation, per-step, model-load, discovery-scan, memory, io, frontend), `what` (call path and frequency), `evidence` (numbers and method), `measured` (true or false), `cost`, `fix` (narrow change, sketched), `gain`, `risk` (what could break, where), `verify` (how to show equivalence and gain), `upstream_dev`, `confidence` (high, medium, low).

## Running Finders At Scale

`workflow.js` in this folder runs one finder agent per area with the scopes, rules and output schema used in practice. Run it with the Workflow tool:

- `scriptPath`: absolute path of `.github/skills/perf-audit/workflow.js`
- `args`: `{ "root": "<main checkout>", "areas": ["installer", "api"], "notes": "optional text for every finder, such as baseline data locations" }` (omit `areas` for all eleven)

It returns one object per area with `findings`, `coverage` and `leads`. Save every finding to its own file, deduplicate across areas (several areas often reach the same root cause), and turn useful leads into findings of their own.

Concurrency per workflow is limited to the number of CPUs minus two. Finders may start servers through `perf-sandbox`; on a 4-core, 16 GB machine keep the total below about eight agents at a time.

## Output

A ranked list of findings with measured evidence, the coverage achieved, and what was not examined.
