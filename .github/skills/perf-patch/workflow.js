export const meta = {
  name: 'perf-patch',
  description: 'Per group of performance candidates: a builder proves each cost and writes a tested patch in isolated copies, then an independent reviewer tries to break each patch',
  whenToUse: 'After perf-audit findings exist; see .github/skills/perf-patch/SKILL.md',
  phases: [
    { title: 'Build', detail: 'reproduce, write and test the minimal patch per candidate in isolated working copies' },
    { title: 'Attack', detail: 'independent reviewer applies each patch and tries to break it' },
  ],
}

// args: { root, findingsDir, patchesDir?, base?, e2eRef?, notes?, groups: [{ id, port, tier, note?, candidates: [{ id, title, findings: [ids], extra }] }] }
const ROOT = args.root || '/home/user/sdnext'
const FINDINGS = args.findingsDir || ROOT + '/tmp/perf/findings'
const PATCHES = args.patchesDir || ROOT + '/tmp/perf/patches'
const SCRIPTS = ROOT + '/.github/skills/perf-sandbox/scripts'
const MKWT = (args.base ? 'BASE=' + args.base + ' ' : '') + 'bash ' + SCRIPTS + '/mkwt.sh'

const RULES = `
SETTING
SD.Next performance pass. Main checkout: ${ROOT} (read-only for you, except that you may create files under ${PATCHES}/ and ${ROOT}/tmp/agents/<candidate id>/). You never commit; accepted patches are applied later by the orchestrator.

Read first, in full: ${ROOT}/.github/skills/perf-patch/SKILL.md (your protocol, verdicts, patch rules), ${ROOT}/.github/skills/perf-sandbox/SKILL.md (working copies, servers, end-to-end check, shared-machine rules) and the "Measuring On A Noisy Machine" section of ${ROOT}/.github/skills/perf-audit/SKILL.md.

Tools: working copies with: ${MKWT} <name>   servers with: bash ${SCRIPTS}/run-app.sh <copy> <port> [args] and bash ${SCRIPTS}/stop-app.sh <copy> <port>   end-to-end check: ${ROOT}/venv/bin/python ${SCRIPTS}/e2e.py --url http://127.0.0.1:<port> --runs 1 ${args.e2eRef ? '--compare ' + args.e2eRef : '(create a reference from an unpatched copy first)'}
Python is ${ROOT}/venv/bin/python; ruff, pylint and py-spy are in the same folder.
${args.notes ? '\nMACHINE AND RUN NOTES\n' + args.notes + '\n' : ''}`

const PER_CANDIDATE_BUILD = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    verdict: { type: 'string', enum: ['patch', 'needs-decision', 'reject'] },
    reproduced: { type: 'string', description: 'What you measured on unmodified code, and how. If it did not reproduce, say so.' },
    design: { type: 'string' },
    measured_before: { type: 'string' },
    measured_after: { type: 'string' },
    gain: { type: 'string', description: 'Measured gain in one or two sentences, with the conditions under which it holds.' },
    who_benefits: { type: 'string' },
    behavior_change: { type: 'string', description: 'The word none, or exactly what a user, extension or API client can observe differently.' },
    patch_files: { type: 'array', items: { type: 'string' }, description: 'Absolute paths, in apply order. Empty when rejected.' },
    files_changed: { type: 'array', items: { type: 'string' } },
    needs_ui_build: { type: 'boolean' },
    checks: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, how: { type: 'string' }, result: { type: 'string' } }, required: ['name', 'result'] } },
    risks: { type: 'array', items: { type: 'string' } },
    upstream_dev: { type: 'string' },
    commit_subject: { type: 'string' },
    commit_body: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['id', 'verdict', 'reproduced', 'gain', 'behavior_change', 'patch_files', 'risks', 'notes'],
}

const BUILD_SCHEMA = {
  type: 'object',
  properties: { group: { type: 'string' }, results: { type: 'array', items: PER_CANDIDATE_BUILD }, notes: { type: 'string' } },
  required: ['group', 'results'],
}

const PER_CANDIDATE_REVIEW = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    verdict: { type: 'string', enum: ['accept', 'accept-with-changes', 'reject'] },
    defects: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, description: { type: 'string' }, evidence: { type: 'string' }, fixed_in_v2: { type: 'boolean' } }, required: ['severity', 'description', 'evidence'] } },
    attempts: { type: 'array', items: { type: 'string' }, description: 'Concrete attacks that did not break the patch, with what you observed.' },
    gain_confirmed: { type: 'boolean' },
    measured: { type: 'string' },
    behavior_change: { type: 'string' },
    final_patch_files: { type: 'array', items: { type: 'string' }, description: 'Absolute paths to apply, in order. Empty when rejected.' },
    residual_risks: { type: 'array', items: { type: 'string' } },
    commit_message_ok: { type: 'string', description: 'The word yes, or what is inaccurate.' },
    notes: { type: 'string' },
  },
  required: ['id', 'verdict', 'defects', 'attempts', 'gain_confirmed', 'measured', 'behavior_change', 'final_patch_files', 'residual_risks', 'notes'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: { group: { type: 'string' }, results: { type: 'array', items: PER_CANDIDATE_REVIEW }, rejections: { type: 'string', description: 'For candidates the builder rejected: agree, or why the rejection looks wrong.' }, notes: { type: 'string' } },
  required: ['group', 'results'],
}

function candidateBlock(c) {
  const files = (c.findings || []).map(f => FINDINGS + '/' + f + '.json').join(', ')
  return `- ${c.id}: ${c.title}\n  Finding report(s): ${files || '(none: the description here is all there is)'}\n  Notes: ${c.extra || 'none'}`
}

function buildPrompt(g) {
  return `${RULES}
YOUR ROLE: builder for group "${g.id}" (size: ${g.tier || 'large'}). Your port: ${g.port}. One working copy per candidate, named after the candidate id.
${g.note ? 'Group note: ' + g.note + '\n' : ''}
Candidates (handle each one separately; each gets its own verdict and its own patch file(s) built against the base commit, so that any subset can be applied on its own):
${g.candidates.map(candidateBlock).join('\n')}

The finders' scratch scripts are under ${ROOT}/tmp/agents/<scope>/ (scope = the report name before its number). Their numbers are claims, not facts.
If an earlier attempt was interrupted, follow "Resuming Interrupted Work" in the perf-patch skill: check ${ROOT}/../wt/<candidate id>* and ${ROOT}/tmp/agents/<candidate id>/.

Follow the builder protocol. Scale the effort to the candidate: for a small, mechanical one, a focused benchmark, an equivalence check, lint and one app start are enough; for a large one be thorough, the reviewer will look for what you skipped. Patch files go to ${PATCHES}/<candidate id>.diff (or .1.diff/.2.diff when stacked). Stop your servers before returning.

Return the structured result with one entry per candidate. Write plainly, for a maintainer who has not seen the finder reports. commit_subject uses the repository's conventional style (for example "perf(installer): ..." or "fix(gallery): ..."), with no AI or model attribution; commit_body says what changed, why it is safe and the measured effect with the method, in a few short lines.`
}

function reviewPrompt(g, b) {
  const built = (b.results || []).filter(r => (r.patch_files || []).length)
  const rejected = (b.results || []).filter(r => !(r.patch_files || []).length)
  return `${RULES}
YOUR ROLE: reviewer for group "${g.id}" (size: ${g.tier || 'large'}). Your port: ${g.port + 1}. Working copies named <candidate id>-rev.

A builder claims each patch below is a safe, measurable improvement. Prove it wrong. Assume a defect exists until you have looked for it properly. If unsure whether a patch is safe, reject it. If you cannot confirm the gain with your own measurement, set gain_confirmed to false.

Candidates:
${g.candidates.map(candidateBlock).join('\n')}

The builder's results for the patched candidates (claims, not facts):
${JSON.stringify(built, null, 1)}
${rejected.length ? '\nCandidates the builder rejected (do not build them; say in "rejections" whether the evidence holds up):\n' + JSON.stringify(rejected.map(r => ({ id: r.id, verdict: r.verdict, reproduced: r.reproduced, notes: r.notes })), null, 1) : ''}

Follow the reviewer protocol for every patched candidate. Corrected patches go to ${PATCHES}/<candidate id>.v2.diff (or .1.v2.diff/.2.v2.diff). Stop your servers before returning.

Return the structured result with one entry per patched candidate. Write plainly, for a maintainer who has seen neither the finder reports nor the builder's results.`
}

const groups = args.groups || []
log('groups: ' + groups.map(g => g.id + '(' + g.candidates.map(c => c.id).join(',') + ')').join(' '))

const results = await pipeline(
  groups,
  (g) => agent(buildPrompt(g), { label: 'build:' + g.id, phase: 'Build', schema: BUILD_SCHEMA }),
  (b, g) => {
    if (!b) return { group: g.id, build: null, review: null }
    const anyPatch = (b.results || []).some(r => (r.patch_files || []).length)
    if (!anyPatch) return { group: g.id, build: b, review: null }
    return agent(reviewPrompt(g, b), { label: 'attack:' + g.id, phase: 'Attack', schema: REVIEW_SCHEMA })
      .then(r => ({ group: g.id, build: b, review: r }))
  }
)

const summary = results.map((r, i) => {
  if (!r) return groups[i].id + '=failed'
  if (!r.build) return r.group + '=no build result'
  return r.group + '[' + (r.build.results || []).map(c => {
    const rv = r.review && (r.review.results || []).find(x => x.id === c.id)
    return c.id + ':' + c.verdict + (rv ? '/' + rv.verdict : '')
  }).join(' ') + ']'
})
log(summary.join(' '))
return results
