export const meta = {
  name: 'tb2-harness-verify',
  description: 'Finish the interrupted verification: fetch + confirm the load-bearing citations in harness/README.md and review grounding / no-design',
  phases: [{ title: 'Verify', detail: 'parallel: two citation-check agents + one internal review' }],
}

const DOC = 'C:/Users/PhilVanEvery/Git/github/pmvanev/harebrain/harness/README.md'

const CITE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    checks: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          url: { type: 'string' },
          resolves: { type: 'boolean' },
          supports_cited_claim: { type: 'string', enum: ['yes', 'partial', 'no', 'cant_tell'] },
          note: { type: 'string' },
          suggested_action: { type: 'string', enum: ['keep', 'flag', 'correct', 'remove'] },
        },
        required: ['url', 'resolves', 'supports_cited_claim', 'note', 'suggested_action'],
      },
    },
  },
  required: ['checks'],
}

// Group A: the flagged-uncertain web sources (blogs/aggregators) + their specific figures
const groupA = [
  'explainx.ai/blog/agent-harness-engineering-terminal-bench-langchain-2026 (does it support: LangChain moved an agent 52.8%->66.5%, +13.7pts, on GPT-5.2-Codex via middleware?)',
  'warp.dev/blog/terminal-bench (does it support: long-horizon/coherence framing; an editable todo/plan beating extended thinking?)',
  'anthropic.com/engineering/effective-context-engineering-for-ai-agents (head/tail truncation, structured note-taking, sub-agent isolation summaries?)',
  'anthropic.com/engineering/effective-harnesses-for-long-running-agents (filesystem-as-state + continuation loop?)',
  'emergentmind.com/topics/swe-agent-frameworks (does it support: SWE-agent linter-reject lifted pass@1 3.8%->12.5%?)',
  'nicolasbustamante.com/blog/model-harness-fit (model-harness fit: Codex apply_patch vs Claude old_string; multi-point swings?)',
  'ghuntley.com/ralph/ (the Ralph loop: re-inject prompt in clean context; many parallel for search, exactly 1 for build/tests?)',
]

// Group B: the academic citations (arxiv/openreview) + their specific numbers
const groupB = [
  'arxiv.org/abs/2305.04091 (Plan-and-Solve beats Zero-shot-CoT, fixes missing-step errors?)',
  'arxiv.org/pdf/2305.11738 (CRITIC: tool-grounded +7.7 F1; self-critique-only lower?)',
  'arxiv.org/html/2303.11366 (Reflexion lifts HumanEval to 91% with execution reward?)',
  'arxiv.org/html/2311.08516v3 (GPT-4 finds errors 52.9%; good at fixing given location?)',
  'openreview.net/pdf?id=IkmD3fKBPQ (self-correction decreases accuracy; GPT-4 GSM8K 95.5->89.0 over 2 intrinsic rounds?)',
  'arxiv.org/html/2604.25850v3 (harness ablation: tools +3.3pp, middleware +2.2pp, long-term memory +5.6pp, system-prompt-only -2.3pp?)',
  'arxiv.org/pdf/2510.23761 (TDFlow decomposition beats monolithic ReAct?)',
  'arxiv.org/html/2601.11868v1 (Terminal-Bench paper: command-not-found 24.1% of failures, executables 9.6%?)',
]

function citePrompt(label, urls) {
  return [
    'You are finishing an interrupted citation-verification pass for ' + DOC + ' (a harness-research notes doc). Read that doc first for the exact claims, then VERIFY the citations below by actually fetching them (WebFetch; WebSearch if a URL 404s but the source likely exists under another path).',
    '',
    'For each entry, the parenthetical is the SPECIFIC figure/claim the doc attributes to it. Report: does the URL resolve; does the fetched content support the cited claim (yes/partial/no/cant_tell); a one-line note (with the corrected URL or figure if the doc is wrong); and a suggested_action (keep / flag / correct / remove).',
    'Be skeptical of exact percentages — confirm the number, not just the topic. If a URL is dead but the real source is findable, give the correct URL in note + action=correct. If you cannot verify, action=flag (do not invent support).',
    '',
    'CITATIONS TO CHECK (' + label + '):',
    ...urls.map((u) => '  - ' + u),
    '',
    'Return the JSON.',
  ].join('\n')
}

const REVIEW_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    grounded: { type: 'boolean' },
    respects_no_design: { type: 'boolean' },
    internally_consistent: { type: 'boolean' },
    links_ok: { type: 'boolean' },
    issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['grounded', 'respects_no_design', 'internally_consistent', 'links_ok', 'issues'],
}

phase('Verify')
const [citeA, citeB, review] = await parallel([
  () => agent(citePrompt('group A — blogs/aggregators', groupA), { label: 'cite:web-sources', phase: 'Verify', schema: CITE_SCHEMA, agentType: 'general-purpose' }),
  () => agent(citePrompt('group B — papers', groupB), { label: 'cite:papers', phase: 'Verify', schema: CITE_SCHEMA, agentType: 'general-purpose' }),
  () =>
    agent(
      [
        'Adversarially review ' + DOC + ' (read the whole file). Check and report issues:',
        '1. grounded — claims attributed to a repo slug / web url / mpl ref, not free-floating.',
        '2. respects_no_design — it must stay APPROACH-only (methodology + technique menu + process); it must NOT design a concrete harness / chart / .mpl code as "the design".',
        '3. internally_consistent — section numbering, the technique-menu table, and the provenance note agree; no contradictions.',
        '4. links_ok — the markdown links (to ../docs/research-summaries/..., ../terminal-bench/...) resolve to real files in the repo (Read/Glob to confirm a couple).',
        'List concrete issues (with line context) so they can be fixed. Do NOT edit the file. Return the JSON.',
      ].join('\n'),
      { label: 'review:internal', phase: 'Verify', schema: REVIEW_SCHEMA },
    ),
])

return { citeA, citeB, review }
