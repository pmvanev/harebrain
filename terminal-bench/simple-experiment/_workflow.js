export const meta = {
  name: 'simple-experiment-docs',
  description: 'Author + verify 5 harebrain-style SVG diagrams and a writeup for the terminal-bench harness-comparison experiment',
  phases: [
    { title: 'Diagrams', detail: 'author 5 SVGs in parallel' },
    { title: 'Verify', detail: 'adversarially check each SVG: valid, theme-adaptive, house-style, factual' },
    { title: 'Writeup', detail: 'synthesize README.md against the verified diagrams + honest results' },
  ],
}

const REPO = 'C:/Users/PhilVanEvery/Git/github/pmvanev/harebrain'
const IMG = REPO + '/terminal-bench/simple-experiment/images'

// ---- shared house-style conventions (passed to every diagram agent) ----
const CONV = [
  'HAREBRAIN SVG HOUSE STYLE (follow exactly):',
  '- Theme-adaptive via CLASS-BASED currentColor plus an @media (prefers-color-scheme: dark) block that redefines the class colors. NEVER hardcode a single-mode palette — the reader views in dark mode.',
  '- Each semantic class sets `color:` to a light value at top, and the dark value inside @media (prefers-color-scheme: dark). Shapes/text use fill="currentColor" or stroke="currentColor" and the class on a wrapping <g>.',
  '- Palette tokens (light / dark): ink #1a1810/#ede2c4 ; muted #5d553f/#a89c7d ; oxblood #8b1f2c/#e09098 ; blueprint #1f4f7a/#88c0e8 ; sage #4f6b3f/#b1c98c ; rule-soft #d4c8a4/#3a3327. Tints are the same hue at ~6-12% alpha (e.g. blueprint-tint rgba(31,79,122,0.08) light / rgba(136,192,232,0.10) dark).',
  '- Color semantics here: blueprint = our custom harness/cage code ; sage = the model/brain and the container ; muted = built-in/neutral ; oxblood = external obstacle (rate limits) or the source/benchmark side ; ink = labels.',
  '- Fonts: Fraunces, serif for headings/labels (often font-style="italic") ; JetBrains Mono, ui-monospace, monospace for code-ish labels.',
  '- Must be a standalone <svg> with an explicit viewBox, role="img", and a descriptive aria-label. No <script>, no external hrefs/images, no raster. Self-contained text only.',
  '- It will be referenced from markdown as an <img>, so the embedded <style> must carry the theme behavior.',
  'Before writing, READ two reference SVGs and mirror their structure/markup exactly (style block, class pattern, <g> grouping):',
  '  ' + REPO + '/docs/research-summaries/terminal-bench/images/glyph.svg',
  '  ' + REPO + '/docs/research-summaries/terminal-bench/images/fig-03-mapping.svg',
].join('\n')

// ---- ground-truth facts (agents may also Read the cited files to confirm) ----
const FACTS = [
  'EXPERIMENT: a harness-comparison on Terminal-Bench. Hold the MODEL fixed (gemini/gemini-2.5-flash) and swap the HARNESS across three agents, measuring resolve rate on a task slice. This probes the "harness lever at a fixed brain" — the same lever the Meta-Harness paper quantified at 6x and the agent-harness-anatomy post showed as Top 30 -> Top 5, both on Terminal-Bench. Distilled in ' + REPO + '/docs/research-summaries/terminal-bench/terminal-bench.md.',
  '',
  'THE THREE HARNESSES (all driven by the same -m gemini/gemini-2.5-flash):',
  '1. terminus-2 — Terminal-Bench BUILT-IN neutral agent. An engineered perceive/think/act loop: structured analysis+plan+commands response, per-keystroke timing, an episode budget, and tenacity RETRIES on provider/LLM errors. The "well-engineered baseline." Reference: it is a tb built-in (no repo file).',
  '2. command-loop — our minimal CUSTOM Python agent. File: ' + REPO + '/terminal-bench/agents/command_loop.py. A thin while-loop: each step makes ONE structured LLM call returning {commands, done}, sends each command via session.send_keys, stops on done or max_steps (default 15; we ran with 20). Catches only JSON-parse errors — an LLM provider error crashes it (no retry). Resolved hello-world earlier at ~88 in / 27 out tokens.',
  '3. mpl-terminal — the harebrain MPL CAGE. Files: ' + REPO + '/terminal-bench/agents/mpl_agent.py (BaseAgent shell) and ' + REPO + '/terminal-bench/agents/terminal.mpl (the chart). The MPL chart OWNS control flow as explicit states Perceive -> Think -> Act -> Done (a 3-tick pipeline; one side-effecting host call per transition; chart var max_steps:=12). Host imports: observe() = capture screen, decide(obs) = one LLM call returning a command or the sentinel "__DONE__", act(cmd) = send keystrokes. The LLM is consulted ONLY at the decide leaf. Fault-tolerant: a host-import exception is logged per-rule ("Error executing actions for rule...") and the sim keeps ticking (a property terminus-2/command-loop lack — but it needs a guard to stop on repeated failures). Resolved hello-world earlier at ~263 in / 43 out tokens.',
  '',
  'THE MODEL (the fixed brain): gemini/gemini-2.5-flash, called through litellm (provider prefix gemini/ reads GEMINI_API_KEY). Held constant across all three harnesses so any resolve-rate delta is attributable to the harness, not the brain. REALITY CHECK: on the free Gemini tier this key hit rate/quota limits (HTTP 429 RateLimitError, and eventually daily-quota exhaustion) — the dominant obstacle to a clean local run.',
  '',
  'THE TASK SLICE (dataset terminal-bench-core==0.1.1, all "easy" difficulty, self-contained / no network):',
  '- hello-world (control): create hello.txt containing "Hello, world!" + newline. ~1 step. Expected: all harnesses pass.',
  '- extract-safely (security): extract archive.tar to /app/solution.txt. Multi-step; earlier BOTH terminus-2 and command-loop failed its test_solution_found.',
  '- fix-permissions (sysadmin): a process_data.sh will not run — diagnose and fix it. Perceive -> diagnose -> act. The one task that resolved in the (rate-limited) multi-task sweep.',
  '- csv-to-parquet (data-science): convert /app/data.csv to /app/data.parquet (needs pandas/pyarrow).',
  '- DROPPED from the slice: grid-pattern-transform — reasoning-hard for Flash, burned the most LLM calls, and timed out at 600s. Noted as excluded.',
  '',
  'HOW WE RUN TERMINAL-BENCH (the stack):',
  '- Windows 11 host. The tb orchestrator CANNOT run natively on Windows (it assumes a POSIX host: builds container paths with backslash -> sends files to \\\\tmp not /tmp; shells out to rm). So it runs as a LINUX PROCESS inside WSL2 Ubuntu (the default distro).',
  '- Docker Desktop is WSL2-backed with integration enabled for Ubuntu; tb talks to the Docker daemon and spins up ONE Linux container PER TASK TRIAL via docker-compose. Each container gets the instruction + Dockerfile; the tests + human oracle are hidden; grading is on the FINAL container state.',
  '- tb is installed as a uv tool pinned to Python 3.13 (3.14 crashes its typer CLI). For the MPL agent, mpl is installed INTO tb venv (uv tool install --with <mplv2 path>).',
  '- The repo is reachable from WSL at /mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain ; run outputs go to the WSL ext4 fs (~/tb-runs), not /mnt/c (Docker IO over /mnt/c is slow).',
  '- The GEMINI_API_KEY is forwarded from the Windows process env into WSL via WSLENV at run time (never printed). Custom agents are loaded with PYTHONPATH=.../terminal-bench/agents + --agent-import-path module:Class.',
  '',
  'EXACT COMMANDS (driven from a Windows PowerShell prompt; WSL commands are double-quoted with absolute paths because single-quoted $-vars/pipes get mangled in the PS->WSL handoff):',
  'PS> $env:WSLENV="GEMINI_API_KEY"',
  'PS> wsl -d Ubuntu -u root -e bash -lc "export PATH=$HOME/.local/bin:$PATH; tb run -d terminal-bench-core==0.1.1 -t hello-world -t extract-safely -t fix-permissions -t csv-to-parquet -a terminus-2 -m gemini/gemini-2.5-flash --n-concurrent 1 --output-path ~/tb-runs/exp1/terminus2"',
  '  # command-loop: add export PYTHONPATH=/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain/terminal-bench/agents; and swap -a terminus-2 for --agent-import-path command_loop:CommandLoopAgent -k max_steps=20',
  '  # mpl-terminal: same PYTHONPATH; --agent-import-path mpl_agent:MplAgent',
  'Free zero-cost check: -a oracle (runs the reference solution, should resolve) ; -a nop (should fail).',
  '',
  'RESULTS WE ACTUALLY OBSERVED (be honest — do not invent clean numbers):',
  '- Clean control (each harness run individually earlier today, before quota exhaustion): hello-world RESOLVED by all three — terminus-2 (1831/362 tok), command-loop (88/27), mpl-terminal (263/43). So at a fixed Gemini Flash brain, all three cages solve the trivial task.',
  '- 4-task sweep at --n-concurrent 2: terminus-2 25% (1/4, only fix-permissions), command-loop 25% (1/4, only fix-permissions) — but HEAVILY contaminated: most trials failed with RateLimitError (the agents crashed mid-task, failure_mode unknown_agent_error / agent_timeout). The mpl run wedged on rate-limit retries against a torn-down container and was killed.',
  '- --n-concurrent 1 retry: 0/4 — by then the Gemini free-tier DAILY quota was exhausted (a single direct API call returned 429).',
  '- CONCLUSION: on the free Gemini tier the harness-lever comparison is UNMEASURABLE — rate/quota limits dominate. Reproducing the experiment needs funded API capacity. The 6x regime (frontier model + hard tasks + many calls) costs real quota to enter — itself part of the answer to "can I reproduce it locally?". The one signal that survived the noise: a real HARNESS-QUALITY axis — terminus-2 retries on provider errors (tenacity) while our minimal agents crash; and the MPL cage is fault-tolerant (keeps ticking past host errors) but needs a stop-on-repeated-failure guard. "Handle provider errors" is itself harness work.',
  '- PAPER-FAITHFUL NEXT STEP (ready, not yet run): same commands with -m openai/gpt-5.2 (the paper #1 model; key set, awaiting billing credit) or -m anthropic/claude-opus-4-8 (the Meta-Harness Opus family).',
].join('\n')

const DIAGRAM_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    wrote: { type: 'boolean' },
    path: { type: 'string' },
    title: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['wrote', 'path', 'title'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    file: { type: 'string' },
    valid_svg: { type: 'boolean' },
    theme_adaptive: { type: 'boolean' },
    house_style: { type: 'boolean' },
    factual: { type: 'boolean' },
    repaired: { type: 'boolean' },
    issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['file', 'valid_svg', 'theme_adaptive', 'house_style', 'factual', 'repaired'],
}

const SPECS = [
  {
    file: 'glyph.svg',
    brief: 'Masthead glyph (wide, about 260x60 viewBox). Motif: a single MODEL/brain disc (sage, label gemini-2.5-flash) on the left, an arrow to THREE small stacked cage tiles (blueprint, labelled terminus-2 / command-loop / mpl), an arrow to a TESTS gate (oxblood, check/cross). The idea: one fixed brain, three cages, graded on the same ruler. Keep it spare and iconographic like the reference glyph.',
  },
  {
    file: 'fig-01-harnesses.svg',
    brief: 'The three harnesses compared (about 660x360). Three columns, one per harness, each a small stack showing its control-flow shape: terminus-2 (muted) = built-in engineered loop with analysis/plan/commands + retries + episode budget; command-loop (blueprint) = thin while-loop, one {commands,done} call per step, max_steps, NO provider-error retry; mpl-terminal (blueprint, emphasized) = MPL chart states Perceive->Think->Act->Done with host imports observe/decide/act, LLM only at the decide leaf, fault-tolerant. A footer line shows all three fed by the same -m gemini/gemini-2.5-flash knob. Caption-worthy: same brain, three cages.',
  },
  {
    file: 'fig-02-model.svg',
    brief: 'The fixed brain — a model card (about 600x300). Center: a brain/disc (sage) labelled gemini-2.5-flash. Spec rows (JetBrains Mono): provider via litellm prefix gemini/ ; role = the constant held across all harnesses ; so any resolve-rate delta is attributable to the cage, not the brain. A distinct oxblood callout box: REALITY — free-tier rate/quota limits (HTTP 429) dominated the run; daily quota exhausted. Tie visually to the harness lever idea.',
  },
  {
    file: 'fig-03-task-slice.svg',
    brief: 'The task slice (about 680x300). Four task cards (dataset terminal-bench-core==0.1.1, all easy, self-contained): hello-world (control — all pass), extract-safely (security — multi-step), fix-permissions (sysadmin — perceive/diagnose/act; the one that resolved), csv-to-parquet (data-science — needs pandas/pyarrow). Each card: name, one-line what-it-exercises, and a small difficulty/expectation marker. Include a muted, struck-through note that grid-pattern-transform was DROPPED (reasoning-hard, timed out at 600s, call-burner).',
  },
  {
    file: 'fig-04-wsl-architecture.svg',
    brief: 'How we run Terminal-Bench (about 680x420). A layered stack, top to bottom: Windows 11 host (note: native tb run = oxblood X, POSIX-host bug \\\\tmp); inside it WSL2 Ubuntu running the tb ORCHESTRATOR as a Linux process (blueprint); it talks to Docker Desktop daemon (sage) which spins ONE Linux container PER TASK TRIAL (sage tiles) — each container gets instruction+Dockerfile, hides tests+oracle, graded on final state. Side annotations: GEMINI_API_KEY forwarded via WSLENV; repo mounted at /mnt/c; outputs to ext4 ~/tb-runs; tb=uv tool py3.13, mpl in tb venv; custom agents via PYTHONPATH + --agent-import-path. Make the arrows show the request path (tb -> daemon -> sibling containers).',
  },
]

phase('Diagrams')

const results = await pipeline(
  SPECS,
  (spec) =>
    agent(
      [
        'You are authoring ONE theme-adaptive SVG diagram for a harebrain research artifact, and writing it to disk.',
        '',
        'OUTPUT FILE (write exactly here with the Write tool): ' + IMG + '/' + spec.file,
        '',
        CONV,
        '',
        'GROUND TRUTH (read the cited files to confirm specifics before drawing):',
        FACTS,
        '',
        'THIS DIAGRAM: ' + spec.brief,
        '',
        'Steps: (1) Read the two reference SVGs to mirror the style/markup. (2) Read any repo files cited above that are relevant to THIS diagram for factual accuracy. (3) Write a single self-contained, theme-adaptive SVG to the output path. Labels must be accurate to the facts. Return the JSON result.',
      ].join('\n'),
      { label: 'draw:' + spec.file, phase: 'Diagrams', schema: DIAGRAM_SCHEMA },
    ),
  (drawn, spec) =>
    agent(
      [
        'You are an adversarial reviewer of ONE SVG diagram. Be strict; repair if needed.',
        '',
        'FILE TO REVIEW (read it): ' + IMG + '/' + spec.file,
        'INTENDED CONTENT: ' + spec.brief,
        '',
        CONV,
        '',
        'GROUND TRUTH for factual accuracy (read cited files if unsure):',
        FACTS,
        '',
        'Check, in order:',
        '1. valid_svg: well-formed single <svg> with an explicit viewBox, role="img", and a descriptive aria-label; no <script>; no external href/image; renders as static.',
        '2. theme_adaptive: MUST contain an @media (prefers-color-scheme: dark) block that redefines the class colors, AND use currentColor via classes. If it hardcodes one palette (no dark block, or fills like fill="#1f4f7a" instead of class+currentColor), it FAILS this check.',
        '3. house_style: palette tokens from the convention; Fraunces for headings/labels and JetBrains Mono/ui-monospace for code-ish labels; color semantics roughly right (blueprint=our code, sage=model/container, oxblood=obstacle/external, muted=built-in).',
        '4. factual: labels match the ground truth (model id, harness names/behaviors, task names, the stack). No invented numbers.',
        '',
        'If ANY check fails, REWRITE the file with the Write tool to fix all issues (keep the intent and layout), then set repaired=true and list what you changed in issues. If everything passes, set repaired=false. Return the JSON verdict.',
      ].join('\n'),
      { label: 'verify:' + spec.file, phase: 'Verify', schema: VERIFY_SCHEMA },
    ),
)

phase('Writeup')

const verifiedList = results.filter(Boolean).map((v) => v.file + ' (valid=' + v.valid_svg + ', themed=' + v.theme_adaptive + ', factual=' + v.factual + ', repaired=' + v.repaired + ')').join('; ')

const writeup = await agent(
  [
    'Write the experiment writeup as a single markdown file with the Write tool.',
    '',
    'OUTPUT FILE: ' + REPO + '/terminal-bench/simple-experiment/README.md',
    '',
    'VOICE/STYLE: match the harebrain house voice — opinionated, precise, tables and short callouts. Mirror the tone of ' + REPO + '/docs/research-summaries/terminal-bench/terminal-bench.md (read it). Reference SVGs as markdown images ![alt](images/<file>) with a short italic caption under each. Do NOT inline SVG.',
    '',
    'The five diagrams now exist in images/ : ' + verifiedList,
    '',
    'GROUND TRUTH — everything you write must come from here (read the cited files to confirm):',
    FACTS,
    '',
    'STRUCTURE:',
    '1. Title + one-italic-line subtitle: what this experiment is (fix the brain, swap the cage, on the Terminal-Bench ruler) and why (the 6x harness-lever question).',
    '2. The masthead glyph image at the very top.',
    '3. "The three harnesses" section — embed fig-01-harnesses.svg; a table of terminus-2 vs command-loop vs mpl-terminal (what each is, control-flow, retry behavior, hello-world tokens).',
    '4. "The fixed brain" — embed fig-02-model.svg; gemini-2.5-flash via litellm; why holding it constant isolates the harness.',
    '5. "The task slice" — embed fig-03-task-slice.svg; the 4 tasks + the dropped grid task.',
    '6. "How we run it" — embed fig-04-wsl-architecture.svg; WSL2 + Docker Desktop + per-task containers + POSIX-host reason; then the EXACT commands in a fenced block (all three harnesses), including the WSLENV key-forward and the oracle/nop free checks.',
    '7. "Results (honest)" — a table + prose. State plainly: the hello-world control passed for all three harnesses individually; the multi-task sweep was rate-limit-dominated (terminus-2 25%/command-loop 25%, both only fix-permissions, most trials crashed on RateLimitError; mpl wedged and was killed); the n-concurrent-1 retry hit 0/4 on an exhausted daily quota. Be explicit that this does NOT measure the harness lever cleanly.',
    '8. "What we learned" — reproduction is gated on API CAPACITY, not just the right model; tie to the terminal-bench summary regime-boundary ("capability sets the ceiling, the harness decides reach") and its $1-100/run cost note; the surviving real signal = the retry/fault-tolerance harness-quality difference (terminus-2 retries; our agents crash; MPL cage keeps ticking but needs a guard).',
    '9. "Paper-faithful next step" — same commands with -m openai/gpt-5.2 (paper #1, key set, awaiting credit) or -m anthropic/claude-opus-4-8 (Meta-Harness Opus family); note results will be slotted in then.',
    '',
    'Keep it tight and skimmable. Return a one-line confirmation of what you wrote.',
  ].join('\n'),
  { label: 'readme', phase: 'Writeup' },
)

return {
  diagrams: results.filter(Boolean),
  writeup,
}
