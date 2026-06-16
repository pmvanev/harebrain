# What we learned building the MPL harness — findings & diagnosis

*The empirical counterpart to [`design.md`](design.md). `design.md` says what we **intended**; this
says what **running it taught us**, and my diagnosis of why. Raw per-run records live in `design.md` §8;
the construct- and soundness-level details live in [`spike-findings.md`](spike-findings.md) and
[`check-soundness.md`](check-soundness.md). Dated 2026-06-15, gpt-5.2 / `terminal-bench-core==0.1.1`,
run locally in WSL2.*

---

## The build, in one pass

1. **Spike** → validated the MPL constructs the chart needs. `@priority` HALT and write-in-`then`/
   read-next-tick both work; **`choose(1){@weight}` is *not* a seeded random draw** (deterministic,
   weight- and seed-independent) — so the §6 stochastic-policy idea was rerouted to a host-seeded RNG.
2. **Walking skeleton** → `terminal_v2.mpl` + `mpl_agent_v2.py`: a sound verify gate (the brain's
   done-claim must pass `check()` to reach Done) + a `@priority` budget HALT. Dry-run green; resolved
   `hello-world` 1/1 live.
3. **check() soundness** → confirmed the hidden grader is injected post-session, so a sound `check()`
   must re-derive observable success from the *public instruction* via a **separate verifier pass**
   (verdict = exit code), never the oracle. The verifier did exactly this in the wild (it wrote a
   correct three-clause predicate for `hello-world`, including "no other files").
4. **Pilots + tuning** → `max_steps` 16→30 let multi-step tasks reach the gate; a graceful-termination
   fix killed a dead-container error flood. Re-pilot: 3/3, gate firing, clean.
5. **Attribution eval** → gate-ON vs gate-OFF ablation, 5 tasks × k=5. **The decisive experiment.**

## What held up

- **The cage works end-to-end and is well-behaved.** Deterministic given seed; the chart owns control
  flow; the LLM is consulted only at the `decide`/`check` leaves; it terminates cleanly (HALT guard +
  host-death detection); it resolves real tasks.
- **The soundness discipline is real.** The separate verifier authored genuinely sound,
  instruction-derived predicates and never touched the hidden grader. The "sound gate" is sound.
- **Cost is a non-issue.** Real metered cost: full 89×5 ≈ $15–30 on gpt-5.2; a 50-trial eval is ~$0.50.
- **Operational reality is captured** (WSL invocation, Windows→WSL key forwarding, Docker fragility,
  endpoint reliability) — see the `terminal-bench-local` memory.

## What didn't — the headline

**The sound verify gate produced ZERO accuracy change — on a strong model *and* a weak one**, and it
wasn't free. Two controlled gate-ON vs gate-OFF ablations, identical 5 tasks × k=5, only the model changed:

| Task | gpt-5.2 ON | gpt-5.2 OFF | gpt-4o-mini ON | gpt-4o-mini OFF |
|---|---|---|---|---|
| fix-permissions | 5/5 | 5/5 | 5/5 | 5/5 |
| csv-to-parquet | 4/5 | 4/5 | 5/5 | 5/5 |
| openssl-selfsigned-cert | 4/5 | 4/5 | 0/5 | 0/5 |
| heterogeneous-dates | 0/5 | 0/5 | 0/5 | 0/5 |
| organization-json-generator | 0/5 | 0/5 | 0/5 | 0/5 |
| **Total** | **52%** | **52%** | **40%** | **40%** |

**Δ = 0 on every task, both models.** Not a single swap. Gate-ON cost +48.8K/+10K tokens on gpt-5.2 and
+49.6K/+2.5K on gpt-4o-mini — for nothing.

## Diagnosis — why the gate didn't move the needle

> **A verify gate is a *rejector*, not a *fixer*. It can say "not done" soundly, but accuracy only moves
> if the model both (1) false-claims-done AND (2) can fix the work once rejected. Neither model hit that
> band — and they missed it for *opposite* reasons.**

The two ablations root-cause it cleanly, from the per-trial `checks` counts and logs:

**Strong model (gpt-5.2) — fails condition (1).** It rarely false-claims done. When it can do a task it
finishes and claims done correctly (`check()` fires and rubber-stamps — pure added cost). When it *can't*,
it doesn't claim done falsely — it gets **stuck**: the 0/5 tasks show `checks=0` on every trial
(`organization-json-generator` looped on `ls`/`cat` and even emitted a Unicode-corrupted `ls -ლა`),
exhausts the budget, and Aborts. The gate never engages where the failures are.

**Weak model (gpt-4o-mini) — satisfies (1), fails condition (2).** It *does* false-claim done — the gate
fired **25×**, including on the failing tasks (`heterogeneous-dates` fired on all 5 trials, twice hitting
`checks=3` = rejected to the retry cap; `openssl` on 2/5). The gate **correctly caught and rejected** the
premature/incomplete work. But the model **couldn't fix it on the bounce** — gpt-4o-mini simply can't
complete openssl (6 deliverables) or the date task, so it retries, stays wrong, submits, and fails 0/5.
Rejecting bad work doesn't create the capability to produce good work.

So the gate is inert at *both* ends of the capability spectrum: too-strong models don't false-claim (they
stall instead), too-weak models can't act on the rejection. The gate adds a **sound signal but no
capability** — and on this task family neither model sat in the narrow sloppy-but-capable band where that
signal would convert to a resolved task.

The gate was the *first* region we built because it was the easiest to make **sound** (the deterministic
check-vs-LLM-judge rule). But **soundness is not impact.** A region only buys accuracy if it targets a
failure mode the brain exhibits *and* gives the brain what it needs to recover. Sound + (absent failure
mode OR un-actionable signal) = inert. *Design corollary:* the gate currently discards what the verifier
knows — it returns only a bool, throwing away *which* assertion failed. Handing that specific failure back
to the fix step (instead of just looping to "try again") is the one change that might pull a
sloppy-but-capable model into the band — untested, and it won't rescue a capability ceiling like
gpt-4o-mini's.

### What this means for the harebrain hypothesis

Harebrain = *fast LLM brain × structured game-AI cage*. This eval sharpens the claim: **a cage region
only buys accuracy when it both targets a failure mode the brain exhibits *and* supplies what the brain
needs to recover.** The verify gate meets neither condition for these models:

- We *predicted* a weaker brain would false-claim → gate helps. The weak-model run **refuted that**: the
  brain did false-claim (gate fired 25×, rejected to the cap on `heterogeneous-dates`), but couldn't act
  on the rejection → still 0/5. A rejector needs a brain capable of fixing; a capability ceiling is
  invisible to it.
- The strong brain doesn't false-claim at all — it stalls. So the gate never even fires where it fails.

So "the cage is the lever" (the Stanford 6×) isn't refuted — but **a verify gate is the wrong region for
both tiers we tested.** The cage's real lever is failure-mode-specific *and* recovery-specific: for a
strong brain that means **progress/stuck-detection** (intervene when the last N commands made no
progress); for a sloppy-but-capable brain it means **actionable rejection** (hand the failed assertion
back, not just "try again"). We built the easiest-to-make-*sound* region first and learned, the honest
way, that sound ≠ load-bearing.

## What the data says the real lever is

**Stuck-detection.** The observed gpt-5.2 failures are no-progress / repeated-failed / corrupted
commands — not premature done. The highest-value next region detects "the last N commands made no
progress / repeated / errored" and intervenes (re-plan, vary approach, escalate). Then attribute *it* the
same gate-ON/OFF way. (Side finding worth its own note: the `ls -ლა` corruption is a model/encoding
artifact in the decide→shell path; a stuck-detector that retries on a non-zero/again-failing command
would also paper over it.)

## Honest caveats

- **Small N.** 5 tasks, 25 trials/condition/model. Three tasks were 0/5 for gpt-4o-mini, two for gpt-5.2 —
  some are likely beyond the base loop regardless of any gate.
- **One task family.** Both evals used the same 5 file/config/data tasks. A different slice (esp. one rich
  in the *sloppy-but-capable* regime) could still show gate value — but the mechanism analysis suggests
  the gate needs a narrow band neither tested tier occupied.
- **Totals are this cut, not a global harness number.** 52% / 40% are these 5 tasks; the leaderboard bar
  (~84–85%) needs the *real* levers, which both ablations show are not our verify gate.

## Implications for the design

- **Keep the gate, dormant.** It's sound and cheap to leave in the chart; both ablations show it isn't
  load-bearing. Don't scale it to 89×5 expecting accuracy — the data says it would only add cost
  (+~50K input tokens/run).
- **The premise test is done.** "Gate helps weaker models" was the hypothesis; the gpt-4o-mini ablation
  **refuted it** (the weak model false-claims but can't fix on rejection). Don't keep chasing the gate as
  the lever.
- **Next, in priority order:** (1) build + attribute a **stuck-detector** region (targets the gpt-5.2
  failure mode *and* where frontier/leaderboard accuracy actually lives); (2) *if* revisiting the gate at
  all, first make rejection **actionable** (feed the failed assertion to the fix step) and test only in a
  sloppy-but-capable band — lower priority, speculative.
- **General principle, earned here:** *attribute every region against the model's actual failure modes
  before believing it's a lever — across the capability range you care about.* Soundness, elegance, and
  "it fires 25×" are not evidence of impact; only a controlled ablation is.
