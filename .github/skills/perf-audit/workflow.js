export const meta = {
  name: 'perf-audit',
  description: 'One finder agent per SD.Next subsystem hunts for real, measurable performance problems and returns structured findings',
  whenToUse: 'Start of a performance pass on SD.Next; see .github/skills/perf-audit/SKILL.md',
  phases: [
    { title: 'Find', detail: 'one finder per subsystem, read-only on tracked files, evidence first' },
  ],
}

// args: { root: '/path/to/main/checkout' (required), areas: ['installer', ...] (optional, default all), notes: 'optional text for every finder', portBase: 7700 }
if (!args || !args.root) throw new Error('args.root (absolute path of the main checkout) is required')
const ROOT = args.root
const NOTES = (args && args.notes) || ''
const PORT_BASE = (args && args.portBase) || 7700

const PREAMBLE = `You are one of several engineers running a performance audit of SD.Next (Python backend with Torch, Diffusers, FastAPI and Gradio 3.x; TypeScript frontend). The main checkout is ${ROOT}. Other engineers cover other subsystems in parallel, so stay inside your scope and pass anything else on as a lead.

Read first: ${ROOT}/.github/skills/perf-audit/SKILL.md (what counts as a finding, measuring rules, recipes, finding format) and ${ROOT}/.github/skills/perf-sandbox/SKILL.md (isolated working copies, running servers, the end-to-end check).

RULES
- Discovery only: do not modify tracked files in ${ROOT}. Scratch scripts, synthetic data and notes go under ${ROOT}/tmp/agents/{{AREA}}/. No git commands that change state in ${ROOT}.
- If you need a server, run it from your own working copy (mkwt.sh {{AREA}}) on port {{PORT}}; one server at a time, stop it when done. Add --quick to launches unless the installer is your scope.
- Evidence beats intuition; an empty list is a valid result. Report only what you would bet survives a skeptical review of both impact and safety. No style nits or sub-millisecond micro-optimizations on paths that run once.
- Platform neutrality: a fix must hold on CUDA, ROCm, IPEX, DirectML, OpenVINO, MPS and CPU, and on Windows, Linux and macOS. If the machine has no GPU, do not present CPU-only effects as GPU effects.
- Check upstream dev for each finding (git -C ${ROOT} show upstream/dev:PATH, if that remote exists) and say whether it is already changed there.
{{NOTES}}
DELIVERABLE
Up to 8 findings ranked by impact times confidence, with the fields of the finding format, plus a coverage note (what you read and measured, what you did not get to) and leads for other scopes.`

const SCOPES = {
  installer: {
    title: 'Launcher and installer: what every launch pays before the server starts',
    files: 'launch.py, installer.py, modules/cmd_args.py, modules/paths.py, modules/paths_internal.py, modules/logger.py, modules/update.py, the installer-triggered part of modules/rocm.py, webui.sh (context).',
    focus: 'Subprocess spawns (git, pip, uv), importlib.metadata scans, network calls (version check, branch listing, submodule fetches), how the quick path is chosen (check_timestamp, check_state, get_state, update_state) and what still runs on it, repeated package checks, logging setup, behavior offline. Real launches in your own working copy are allowed (they move only that copy\'s submodules), never with --upgrade, --reinstall or --reset; mock git and pip to study those paths.',
  },
  'startup-imports': {
    title: 'Server startup: import-time and init-time cost',
    files: 'webui.py, modules/loader.py, modules/shared*.py, options*.py, ui_definitions.py, errors.py, timer.py, json_helpers.py, server.py, modules/api/models.py, localization.py, theme.py, modular*.py, and the init-time behavior of devices.py, sd_hijack_*.py, patches.py, sd_samplers*.py.',
    focus: 'Everything between "Starting module webui" and "Local URL": heavy third-party imports needed only by rare features (lazy import only where import-order side effects allow it; read the comments in modules/loader.py), repeated init work, expensive module-level code, garbage-collector cost during startup, compile probes.',
  },
  'ui-build': {
    title: 'Gradio UI construction, page-load payload, per-event overhead',
    files: 'modules/ui.py and modules/ui_*.py (including ui_extra_networks*.py), gr_hijack.py, gr_tempdir.py, scripts_manager.py, script_loading.py, script_callbacks.py, scripts*.py, extensions.py, non-vendored scripts/*.py.',
    focus: 'Size and composition of GET / and /config (what dominates, what is duplicated per tab), create_ui cost, script loading, settings UI, work on every Gradio event or submit, refresh actions that rebuild more than needed.',
  },
  frontend: {
    title: 'Browser-side cost in the core TypeScript UI',
    files: 'ui/*.ts (source of ui/dist). Read-only context: ui/css, modules/ui_javascript.py, extensions-builtin/sdnext-modernui (submodule, never propose edits there).',
    focus: 'Measure with Playwright and Chromium against your own server: navigation timing, requests on load, long tasks, DOM size, idle CPU, timers and observers that never stop (also when the tab is hidden), whole-document queries inside loops or mutation callbacks, layout thrashing, extra-networks filtering and sorting with thousands of cards, the gallery, autocomplete dataset loading, the hints and localization pass. Propose source changes only; a change needs an ui/dist rebuild.',
  },
  discovery: {
    title: 'Model and network discovery: scans, caches, hashing, metadata',
    files: 'modules/modelloader.py, sd_checkpoint.py, files_cache.py, hashes.py, modeldata.py, model_probe.py, sd_detect.py, sd_vae.py, sd_unet.py, model_te.py, model_tools.py, models_hf.py, storage.py, modelstats.py, textual_inversion.py (listing and loading), modules/lora/ listing and metadata, modules/civitai/, upscaler listing, the data side of modules/ui_extra_networks*.py, modules/api/loras.py.',
    focus: 'Cost that scales with the library: directory walks, stat per file, hashing, sidecar reads, safetensors header reads, preview and thumbnail lookups, quadratic lookups, cache keys and invalidation, full rescans triggered by ordinary actions. Build synthetic libraries (thousands of tiny files) under your scratch folder.',
  },
  'model-load': {
    title: 'Model load, offload, quantization, device and memory management',
    files: 'modules/sd_models*.py, sd_modules.py, sd_offload*.py, model_quant.py, devices.py, memstats.py, memmon.py, transformer_cache.py, sd_hijack_accelerate.py, sd_hijack_safetensors.py, sd_hijack_hfhub.py, modular*.py, pipelines/generic*.py and non-vendored pipelines/model_*.py.',
    focus: 'Load and switch overhead beyond weight I/O: repeated module traversals, redundant moves and casts, hooks that run on every forward or step, memory-stat polling in hot paths, devices.torch_gc callers and the cost of each call.',
  },
  processing: {
    title: 'Generation pipeline: fixed per-generation and per-step overhead',
    files: 'modules/processing*.py, txt2img.py, img2img.py, shared_state.py, progress.py, sd_samplers*.py, sd_hijack_schedulers.py, modules/vae/ preview decoders (sd_vae_micro.py, sd_vae_taesd.py, sd_vae_remote.py), masking.py, history.py, call_queue.py, modules/attention/.',
    focus: 'Python-side work around the model call: step callback, live preview decoding (frequency, cost, network retries), latent copies and transfers, state and progress updates, sampler re-creation, logging, history, batch handling, VAE decode path conversions.',
  },
  'prompts-lora': {
    title: 'Prompt path and LoRA activation',
    files: 'modules/prompt_parser*.py, processing_prompt.py, styles.py, extra_networks.py, modules/lora/*.py, textual_inversion.py, token_merge.py, sd_hijack_te.py, ipadapter.py.',
    focus: 'Per-generation prompt work (styles, wildcards, parsing, tokenizing, embedding cache effectiveness and keys, hires and batch re-encodes) and LoRA activation (disk reloads versus cache, delta math, backups, loops over all modules, re-application when nothing changed). Use a real-size tokenizer: tiny test models hide tokenizer costs.',
  },
  'images-io': {
    title: 'Saving and serving images and video',
    files: 'modules/images.py, modules/image/*.py, infotext*.py, generation_parameters_copypaste.py, ui_gallery.py, modules/api/gallery.py, helpers.py, upload.py, mime.py, video.py, modules/video_models/video_save.py and video_utils.py, postprocessing.py, extras.py.',
    focus: 'Double encodes, metadata building, filename generation in large folders, grids, gallery thumbnails and folder listing with tens of thousands of files, base64, conversions between PIL, numpy and torch, blocking work on the event loop.',
  },
  api: {
    title: 'API layer, middleware, polling endpoints, queue',
    files: 'modules/api/*.py, call_queue.py, progress.py, scheduler*.py, server.py, memstats.py, the server setup in webui.py; ui/*.ts for which endpoints are polled and how often.',
    focus: 'Per-request middleware cost (logging, gzip level and content types, auth), polled endpoints and their cost, blocking calls inside async handlers, subprocesses per request, static data recomputed per request, serialization hot spots, large responses.',
  },
  features: {
    title: 'Feature paths: control, detailer, upscalers, XYZ grid, video, caption, background removal',
    files: 'modules/control/ (not control/proc), modules/detailer/, modules/postprocess/*_model.py, upscaler*.py, postprocessing.py, scripts_postprocessing.py, modules/video_models/, modules/ltx/, modules/framepack/ (not framepack/pipeline), modules/caption/, modules/rembg, scripts/xyz*.',
    focus: 'Model reloads or file re-reads inside loops, per-frame or per-tile conversions and transfers, cache clears that defeat caching, memory held while assembling outputs. Most of this cannot run end to end without real models; read call paths carefully, micro-benchmark the pure-Python parts, and mark estimates.',
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    scope: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          category: { type: 'string', enum: ['startup', 'page-load', 'request', 'generation', 'per-step', 'model-load', 'discovery-scan', 'memory', 'io', 'frontend'] },
          what: { type: 'string' },
          evidence: { type: 'string' },
          measured: { type: 'boolean' },
          cost: { type: 'string' },
          fix: { type: 'string' },
          gain: { type: 'string' },
          risk: { type: 'string' },
          verify: { type: 'string' },
          upstream_dev: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['title', 'files', 'category', 'what', 'evidence', 'measured', 'cost', 'fix', 'gain', 'risk', 'verify', 'upstream_dev', 'confidence'],
      },
    },
    coverage: { type: 'string' },
    leads: { type: 'string' },
  },
  required: ['scope', 'findings', 'coverage'],
}

const wanted = args && Array.isArray(args.areas) && args.areas.length ? args.areas : Object.keys(SCOPES)
const keys = wanted.filter(k => SCOPES[k])
const unknown = wanted.filter(k => !SCOPES[k])
if (unknown.length) log('unknown areas skipped: ' + unknown.join(', '))
log('areas: ' + keys.join(', '))

phase('Find')
const results = await parallel(keys.map((k, i) => () => {
  const s = SCOPES[k]
  const prompt = PREAMBLE.replaceAll('{{AREA}}', k).replaceAll('{{PORT}}', String(PORT_BASE + i * 2)).replace('{{NOTES}}', () => (NOTES ? '\nNOTES FROM THE ORCHESTRATOR\n' + NOTES + '\n' : '')) + '\n\nYOUR SCOPE (key: ' + k + '): ' + s.title + '\nFiles: ' + s.files + '\nFocus: ' + s.focus
  return agent(prompt, { label: 'find:' + k, phase: 'Find', schema: FINDINGS_SCHEMA }).then(r => (r ? { ...r, scope: k } : null))
}))

const ok = results.filter(Boolean)
const failed = keys.filter((k, i) => !results[i])
if (failed.length) log('finders without a result: ' + failed.join(', '))
log('finders returned: ' + ok.length + '/' + keys.length + ', findings: ' + ok.reduce((n, r) => n + r.findings.length, 0))
return ok
