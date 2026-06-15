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

**The sound verify gate produced ZERO accuracy change on gpt-5.2**, and it wasn't free.

| Task | gate-ON | gate-OFF | Δ |
|---|---|---|---|
| fix-permissions | 5/5 | 5/5 | 0 |
| openssl-selfsigned-cert | 4/5 | 4/5 | 0 |
| csv-to-parquet | 4/5 | 4/5 | 0 |
| heterogeneous-dates | 0/5 | 0/5 | 0 |
| organization-json-generator | 0/5 | 0/5 | 0 |
| **Total** | **52% (13/25)** | **52% (13/25)** | **0** |

Not even a per-task swap. Gate-ON cost **+48.8K input / +10K output tokens** (16 verifier calls) over the
identical-everything-else ablation, for no gain.

## Diagnosis — why the gate didn't move the needle

> **A verify gate guards exactly one failure class — premature / false done-claims — and on gpt-5.2 that
> class barely occurs. So the gate sits precisely where the failures *aren't*.**

The logs root-cause it cleanly. Every trial splits into two behaviors, and the gate is irrelevant to both:

- **When the brain can do the task, it does — and claims done correctly.** `check()` fires and
  rubber-stamps work that was already right. No change in outcome; pure added cost.
- **When the brain can't, it doesn't false-claim done — it gets *stuck*.** The 0/5 tasks show `checks=0`
  on *every* trial: the solver never reaches a done-claim. `organization-json-generator` looped on
  `ls`/`cat` re-exploration and even emitted a Unicode-corrupted command `ls -ლა` (Georgian chars for
  `-la`); it exhausts the step budget and hits Abort. The gate never engages.

The gate was the *first* region we built because it was the easiest to make **sound** (the deterministic
check-vs-LLM-judge rule). But **soundness is not impact.** A region only buys accuracy if it targets a
failure mode the brain actually exhibits. Sound + targeting an absent failure mode = inert.

### What this means for the harebrain hypothesis

Harebrain = *fast LLM brain × structured game-AI cage*. This eval sharpens the claim: **the cage's value
is failure-mode-specific, and the brain's competence determines its failure mode.**

- A **weaker brain** is over-confident → false-claims-done → a verify gate is a real lever.
- A **stronger brain** rarely false-claims → it fails by **getting stuck** (no-progress loops, repeated
  or malformed commands) → the lever is **progress / stuck-detection, planning, better exploration** —
  *not* a verify gate.

So "the cage is the lever" (the Stanford 6×) is consistent with our null result: the lever is real, but
*which region is the lever* depends on the model. We pointed our first region at the wrong failure mode
for this model. That is a design lesson, not a refutation — and exactly what an attribution ablation is
for.

## What the data says the real lever is

**Stuck-detection.** The observed gpt-5.2 failures are no-progress / repeated-failed / corrupted
commands — not premature done. The highest-value next region detects "the last N commands made no
progress / repeated / errored" and intervenes (re-plan, vary approach, escalate). Then attribute *it* the
same gate-ON/OFF way. (Side finding worth its own note: the `ls -ლა` corruption is a model/encoding
artifact in the decide→shell path; a stuck-detector that retries on a non-zero/again-failing command
would also paper over it.)

## Honest caveats

- **Small N.** 5 tasks, 25 trials/condition. Two tasks were 0/5 under both conditions — possibly beyond
  this base loop regardless of any gate.
- **Model-specific.** This is a gpt-5.2 result. The gate may still earn its keep on a weaker model where
  premature-done is common — **untested**.
- **52% is this cut, not a global harness number.** The leaderboard bar (~84–85%) needs the *real* levers,
  which this eval shows are not our verify gate.

## Implications for the design

- **Keep the gate, dormant.** It's sound and cheap to leave in the chart; it just isn't load-bearing for
  capable models. Don't scale it to 89×5 expecting accuracy — the data says it would only add cost.
- **Next:** (1) build + attribute a **stuck-detector** region (the data-driven lever); and/or (2)
  re-attribute the gate on a **weaker model** to test its design premise directly.
- **General principle, earned here:** *attribute every region against the model's actual failure modes
  before believing it's a lever.* Soundness, elegance, and "it fires" are not evidence of impact — only a
  controlled ablation is.
