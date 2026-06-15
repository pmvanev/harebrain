export const meta = {
  name: 'tb2-harness-research',
  description: 'Gather repo research + deep web + the MPL repo, synthesize APPROACH notes for designing a TB-2 harness into mpl_harness/README.md (no harness design)',
  phases: [
    { title: 'Gather', detail: 'parallel: repo research clusters + web research + MPL repo review' },
    { title: 'Synthesize', detail: 'write the approach notes into mpl_harness/README.md' },
    { title: 'Review', detail: 'adversarially check grounding, honesty, and the no-design constraint' },
  ],
}

const REPO = 'C:/Users/PhilVanEvery/Git/github/pmvanev/harebrain'
const SUM = REPO + '/docs/research-summaries'
const MPLV2 = 'C:/Users/PhilVanEvery/Git/github/lostinplace/mplv2'
const README = REPO + '/terminal-bench/mpl_harness/README.md'

const HARNESS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    cluster: { type: 'string' },
    takeaways: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          principle: { type: 'string' },
          tb2_relevance: { type: 'string' },
          source_slug: { type: 'string' },
        },
        required: ['principle', 'tb2_relevance', 'source_slug'],
      },
    },
  },
  required: ['cluster', 'takeaways'],
}

const WEB_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    topic: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          technique: { type: 'string' },
          why_it_helps: { type: 'string' },
          source_url: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['technique', 'why_it_helps', 'source_url', 'confidence'],
      },
    },
  },
  required: ['topic', 'findings'],
}

const MPL_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    area: { type: 'string' },
    capabilities: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          mpl_feature: { type: 'string' },
          harness_use: { type: 'string' },
          ref: { type: 'string' },
          supported: { type: 'string', enum: ['yes', 'partial', 'no/unknown'] },
        },
        required: ['mpl_feature', 'harness_use', 'ref', 'supported'],
      },
    },
  },
  required: ['area', 'capabilities'],
}

// ---------- gather: repo research clusters ----------
const repoClusters = [
  { cluster: 'harness-core', slugs: ['harness-engineering', 'agentic-harness-engineering', 'agent-harness-anatomy', 'meta-harness', 'nlah'] },
  { cluster: 'ruler-evals-failure-modes', slugs: ['terminal-bench', 'agentic-benchmarks', 'benchmarks-broken', 'benchmark-contamination', 'eval-driven-iteration', 'evaluation-engineering', 'hallucination-recitations'] },
  { cluster: 'control-verification-statecharts', slugs: ['llm-modulo', 'harel', 'dynamic-workflows', 'assessing-judges', 'judge-debate', 'autorubric', 'complexbench', 'advanced-if'] },
  { cluster: 'systems-memory-orchestration', slugs: ['agentos', 'agentspec', 'os-symphony', 'hart', 'tri-agent-clarification', 'mebn-prowl', 'project-vend', 'replit-database', 'collabeval', 'llm-attribution-survey', 'rag-attribution-survey', 'openclaw-emails'] },
]

const repoThunks = repoClusters.map((c) => () =>
  agent(
    [
      'You are mining this repo\'s research summaries for lessons that inform HOW TO DESIGN AN AGENT HARNESS for Terminal-Bench 2.0 (a benchmark of hard, real terminal tasks graded on final container state).',
      'Read each summary markdown file in your cluster (skim the less-relevant ones; deep-read the harness-relevant ones):',
      ...c.slugs.map((s) => '  ' + SUM + '/' + s + '/' + s + '.md'),
      '',
      'For each load-bearing idea, extract a takeaway: a harness-design PRINCIPLE, why it matters for TB-2 specifically (tie to its failure classes — Execution / Coherence / Verification — or to resolve rate, cost, determinism, or auditability), and the source slug.',
      'Only include genuinely harness-relevant principles; skip plot summary. Aim for the 5-12 strongest takeaways across the cluster. Return the JSON.',
    ].join('\n'),
    { label: 'repo:' + c.cluster, phase: 'Gather', schema: HARNESS_SCHEMA },
  ),
)

// ---------- gather: deep web research ----------
const webTopics = [
  {
    topic: 'terminal-bench-specific harnesses',
    brief: 'How the top Terminal-Bench agents/harnesses are actually built and why they score well. Look into: Terminus / Terminus-2 (the tb neutral agent) design; Codex CLI, Capy, LemonHarness, NexAU-AHE, ForgeCode (leaderboard leaders); the Harbor framework; the Terminal-Bench papers\' error analysis and what it implies for harness design; the agent-harness-anatomy / LangChain "anatomy of an agent harness" writeup. tbench.ai docs and blog.',
  },
  {
    topic: 'coding-agent harness/scaffold best practices',
    brief: 'General best practices for building effective coding-agent harnesses/scaffolds: the agent loop, context/window management, the "Ralph loop" continuation pattern, AGENTS.md / filesystem-as-memory, tool surface design (bash vs dedicated tools), prompt/system design for agentic coding, parallelism. Anthropic/Claude Code engineering posts, LangChain, swe-agent / mini-swe-agent, OpenHands design.',
  },
  {
    topic: 'verification, planning, and recovery loops',
    brief: 'Techniques that raise agent task success: plan-then-execute, self-verification / reflection / critic loops, test-driven agent loops, reducing premature "done", bounded retry + error recovery, when self-checking helps vs hurts. Cite papers/posts (Reflexion, self-refine, plan-and-solve, verifier/critic patterns) and any TB-relevant evidence.',
  },
  {
    topic: 'terminal interaction and tool grounding',
    brief: 'Patterns for an agent driving a real terminal/tmux and avoiding common failures: reducing "command not found / not in PATH" (the #1 TB-2 command error), installing/grounding tools before use, handling long-running commands and interactivity, sandbox/container interaction, output parsing. Cite sources.',
  },
]

const webThunks = webTopics.map((t) => () =>
  agent(
    [
      'You are doing DEEP WEB RESEARCH to inform how to design an agent harness for Terminal-Bench 2.0. Use WebSearch (several focused queries) and WebFetch (open the 2-4 best primary sources) — do not answer from memory.',
      '',
      'TOPIC: ' + t.topic,
      'SCOPE: ' + t.brief,
      '',
      'Rules: every finding MUST carry a real source_url you actually fetched. If you cannot verify a claim against a fetched source, mark confidence "low" and say so in why_it_helps. Prefer primary sources (papers, official docs, engineering blogs) over listicles. Extract concrete, actionable TECHNIQUES (not generic advice), each with why it helps a terminal coding agent. Return 5-10 findings as JSON.',
    ].join('\n'),
    { label: 'web:' + t.topic.split(' ')[0], phase: 'Gather', schema: WEB_SCHEMA, agentType: 'general-purpose' },
  ),
)

// ---------- gather: MPL repo review ----------
const mplThunks = [
  () =>
    agent(
      [
        'Review the MPL v2 LANGUAGE to map its features onto agent-harness primitives. MPL is a hierarchical-state-machine / discrete-simulation DSL; we intend to author an agent harness AS an MPL chart (states = control flow, host imports = side effects, the LLM at a decide leaf).',
        'Read these docs in full:',
        '  ' + MPLV2 + '/docs/0 - Overview.md',
        '  ' + MPLV2 + '/docs/1 - Stopwatch.md',
        '  ' + MPLV2 + '/docs/2 - Feature Status.md',
        '  ' + MPLV2 + '/docs/3 - REPL.md',
        '  ' + MPLV2 + '/README.md',
        '  ' + MPLV2 + '/AUDIT.md',
        '',
        'For each language capability relevant to building a harness (states/machines/regions, signals, typed vars, host imports, choose/spread, conflict groups @priority/@weight/@conflict, regionmaps, instantiation `new`, /SIM and /TICK, seed/determinism, ENTER/EXIT lifecycle, anything else), record: the mpl_feature, how it could serve a harness (plan/verify/retry/blackboard/parallel-actions/budget/termination), a doc ref, and whether it is supported (check Feature Status / AUDIT for gaps and mark partial / no-unknown honestly). Return JSON.',
      ].join('\n'),
      { label: 'mpl:language', phase: 'Gather', schema: MPL_SCHEMA },
    ),
  () =>
    agent(
      [
        'Review the MPL v2 SDK and EXAMPLES to extract concrete embedding patterns for building an agent harness as a chart.',
        'Read: ' + MPLV2 + '/mpl/sdk.py , ' + MPLV2 + '/mpl/host.py , ' + MPLV2 + '/mpl/__init__.py , and list ' + MPLV2 + '/examples/ then read the most harness-relevant examples (e.g. host_calls, conflict_groups, policy, squad_tactics, factory, town, starship, arena).',
        '',
        'Extract: the embedding API (load / Simulation / tick / register_host / reading state / send / snapshot-restore if any / seed), the host-import contract and type marshalling, and reusable CHART PATTERNS each example demonstrates that map to harness needs (a perceive-decide-act loop, choosing among competing actions via choose/@priority, tracking many items via regionmaps, retry/guard structures, sub-machine composition). For each, record mpl_feature (or pattern), harness_use, a file ref, and supported(yes/partial/no-unknown). Return JSON.',
      ].join('\n'),
      { label: 'mpl:sdk-examples', phase: 'Gather', schema: MPL_SCHEMA },
    ),
]

phase('Gather')
const gathered = await parallel([...repoThunks, ...webThunks, ...mplThunks])
const ok = gathered.filter(Boolean)
log('gather complete: ' + ok.length + '/' + (repoThunks.length + webThunks.length + mplThunks.length) + ' agents returned')

const bundle = JSON.stringify(ok, null, 2)

phase('Synthesize')
const synth = await agent(
  [
    'Synthesize the gathered research into APPROACH NOTES for designing the best-possible Terminal-Bench 2.0 harness, and write them into the existing charter README.',
    '',
    'HARD CONSTRAINT: do NOT design a harness. No concrete chart, no state list as "the design", no .mpl code, no "here is our harness". Produce a METHODOLOGY + a TECHNIQUE MENU with trade-offs + mappings. The user explicitly said "don\'t try to design one yet."',
    '',
    'OUTPUT FILE: ' + README + ' — READ it first, KEEP the existing charter content intact, and ADD a new top-level section titled "## Research notes — how to approach the best-possible TB-2 harness" placed BEFORE the existing "## Status" section. Write the full updated file. Match the existing house voice (opinionated, tight, tables, > callouts).',
    '',
    'The section should cover, grounded in the bundle below (attribute claims — repo summary slug, a web source_url, or an mpl ref — and carry web confidence/uncertainty honestly):',
    '1. A short framing: what a TB-2 harness must do well (tie to the Execution/Coherence/Verification failure taxonomy and the cost/determinism/auditability axes).',
    '2. What the leaderboard leaders + the literature actually do (the web findings) — the recurring harness techniques, with sources.',
    '3. A TECHNIQUE MENU: for each candidate harness capability (planning, verification-before-done, bounded retry/recovery, blackboard/context management, tool grounding, parallel/sub-agent actions, action selection), give: what it is, the evidence it helps, the trade-off/cost, the TB-2 failure class it attacks, and HOW MPL could express it (map to the mpl features from the bundle, noting any MPL gaps honestly).',
    '4. A recommended PROCESS, not a product: eval-driven iteration (start from terminus-2 as baseline, add one region, dry-run on a hard subset with -k 5, keep/cut), and the hand-author-now vs Meta-Harness-search-later split.',
    '5. Open questions / risks to resolve before designing (e.g. can verify run the hidden tests? determinism at the decide leaf, cost ceilings, MPL feature gaps).',
    '',
    'GATHERED RESEARCH BUNDLE (JSON):',
    bundle,
    '',
    'Return a one-line confirmation of what you wrote.',
  ].join('\n'),
  { label: 'synthesize-readme', phase: 'Synthesize' },
)

phase('Review')
const REVIEW_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    grounded: { type: 'boolean' },
    honest_about_uncertainty: { type: 'boolean' },
    respects_no_design_constraint: { type: 'boolean' },
    actionable: { type: 'boolean' },
    charter_preserved: { type: 'boolean' },
    repaired: { type: 'boolean' },
    issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['grounded', 'honest_about_uncertainty', 'respects_no_design_constraint', 'actionable', 'charter_preserved', 'repaired'],
}
const review = await agent(
  [
    'Adversarially review the new "Research notes" section in ' + README + ' (read the whole file).',
    'Check: (1) grounded — claims attributable to a repo slug, a web URL, or an mpl ref, not free-floating; spot-check that web URLs look real (not fabricated) and that uncertain web claims are flagged. (2) honest_about_uncertainty. (3) respects_no_design_constraint — it must NOT design a concrete harness / chart / .mpl code; it should be approach + technique-menu + process only. (4) actionable. (5) charter_preserved — the original charter content (the hope, the starting point, the bar table, the honest constraints, the layout) is still present and intact.',
    'If it FAILS (3) (crosses into designing one) or drops the charter, or has fabricated-looking citations, REPAIR the file with the Write tool (trim the design, restore the charter, fix citations) and set repaired=true with details in issues. Otherwise repaired=false. Return the JSON verdict.',
  ].join('\n'),
  { label: 'review', phase: 'Review', schema: REVIEW_SCHEMA },
)

return { gathered: ok.length, synth, review }
