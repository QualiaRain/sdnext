---
name: perf-sandbox
description: "Run SD.Next in isolated, disposable working copies for measuring and testing changes: git worktrees with their own submodules, one server per port, a tiny offline test model, and a bit-exact end-to-end generation check."
argument-hint: "Optionally name the working copy and port to prepare, or 'setup' for the one-time environment preparation"
---

# Performance Sandbox

Run the real app from throwaway copies of the repository, so that measurements, experiments and patch tests never touch the main checkout and several agents can work side by side on one machine.

## When To Use

- Before measuring anything that needs a running server (startup, page load, API latency, generation)
- When testing a patch against the unmodified code (one copy per variant)
- When several agents or workflows test different changes at the same time
- The skills `perf-audit`, `perf-patch` and `perf-land` build on this one

## Guidance

- Consult `.github/instructions/core.instructions.md` for runtime rules (startup ordering, platform neutrality).
- The scripts are Bash and expect Linux or macOS with git 2.31 or newer. On Windows run them from WSL or Git Bash, or follow the same steps by hand.

## One-Time Setup

Run from the main checkout root.

1. Python environment: the first `./webui.sh --uv --test` creates `venv/` and installs everything. As root the flag goes first: `./webui.sh -f --uv --test` (webui.sh stops reading its own flags at the first one it does not know). Do not install project dependencies by hand.
2. JavaScript tooling (only for UI work): Node 24 or newer, then `pnpm install --frozen-lockfile`.
3. Tiny test model, built offline from random weights in about a second:
   `venv/bin/python .github/skills/perf-sandbox/scripts/make_tiny_sd.py models/Diffusers/tiny-sd`
   Select it once (Settings, `config.json` key `sd_model_checkpoint: "Diffusers/tiny-sd"`, or `POST /sdapi/v1/options`). Working copies copy `config.json` from the main checkout, so they start with the same model.
   With Hugging Face access, small real pipelines are also useful for other model families: `hf-internal-testing/tiny-stable-diffusion-xl-pipe`, `tiny-flux-pipe`, `tiny-sd3-pipe`.
4. Optional measuring tools, not installed by the repo: `venv/bin/pip install py-spy` for sampling profiles of a running server, and Playwright with Chromium for browser measurements (for example `npm install --prefix tmp/playwright playwright` and `npx --prefix tmp/playwright playwright install chromium`). Measurement tools are the one exception to the rule against installing by hand.

## Working Copies

```bash
S=.github/skills/perf-sandbox/scripts
bash $S/mkwt.sh base          # prints /path/to/wt/base
bash $S/mkwt.sh my-change     # one copy per variant you want to compare
```

- A copy is a git worktree in `<parent of the main checkout>/wt/<name>` (override with `SD_WT_ROOT`), checked out detached at the main checkout's `HEAD` (override with `BASE=<commit>`).
- Its submodules are real checkouts cloned from the local object store, so there is no network access and no sharing of submodule work trees.
- `venv` and `node_modules` are symlinks to the main checkout. Treat them as read-only: never `pip install`, `uv pip install` or `pnpm install` from a copy, and never launch with `--upgrade`, `--reinstall` or `--reset`.
- Record your change with `git -C <copy> diff HEAD -- <files> > some.diff` and switch it off and on with `git apply -R` / `git apply`. Do not use `git stash`: the stash is shared by all worktrees.
- Remove a copy you created: `git worktree remove --force <copy>`, then `git worktree prune`.

## Running The App

```bash
bash $S/run-app.sh <copy> <port> [extra launch.py args]   # waits until the API answers, prints pid and log path
bash $S/stop-app.sh <copy> <port>
bash $S/stop-app.sh --all                                 # stop every server any copy started; only when nothing else on the machine still needs one
```

- The log is `<copy>/tmp/server-<port>.log` and includes per-phase timings (`Startup time`, `Installer time`, model load, generation timers). Debug logging is on by default.
- Models come from the main checkout's `models/` (override with `SD_MODELSDIR`, the variable `launch.py` itself reads). For synthetic libraries use flags such as `--lora-dir` or `--data-dir` that point into the copy's `tmp/`, never write into the shared `models/`.
- Torch threads: the script sets `OMP_NUM_THREADS=1` and the loader then uses half the cores. This keeps several servers usable on one machine and keeps hashes stable. Export `OMP_NUM_THREADS` to override, and compare hashes only between servers started the same way.
- Memory guard: the script waits until 3 GB is available (`SD_MIN_FREE_MB`) and gives up after 20 minutes with exit code 2. One idle server with the tiny model takes about 1.3 GB.
- Add `--quick` to skip the version check: each normal launch makes two unauthenticated GitHub API calls, and the hourly limit is shared by everything on the machine. Leave it out only when the installer itself is under test.
- The first launch in a fresh copy takes the installer's full path, which fast-forwards that copy's submodules to their branch heads. That is expected and only affects the copy.
- `launch.py --test` also binds a port. Pass `--port` with a free port when another server runs, otherwise it fails with "Server failed to start".

## End-To-End Check

```bash
venv/bin/python $S/e2e.py --url http://127.0.0.1:<port> --runs 1 --json ref.json        # once, on an unmodified copy
venv/bin/python $S/e2e.py --url http://127.0.0.1:<port> --runs 1 --compare ref.json     # on the changed copy; exit 1 on any difference
```

- Cases: txt2img 512x512 20 steps (with and without saving), 256x256 4 steps, batch of 4, and img2img from the first result.
- The hashes are of decoded pixels, so they detect any change in generated output. They depend on model, thread count and hardware: create the reference with the same `run-app.sh` setup on the same machine.
- Timings from `e2e.py` are wall time per request. On a shared machine they are only indicative; see `perf-audit` for how to measure.

## Shared-Machine Rules

- Use only the ports assigned to you; never use another agent's server.
- Stop only processes you started (by pid file). Never `pkill` or `killall` by name. `stop-app.sh` checks that a pid still belongs to the server before signalling it.
- No commits, stash, branch or config changes from agents unless the task says so.
- Stop your server as soon as you have what you need.

## Output

Report which copy and port you used, the base commit, and any deviation from these defaults (threads, models folder, flags).
