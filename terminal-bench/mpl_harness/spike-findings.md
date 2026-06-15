# SPIKE findings — MPL constructs the v2 harness depends on

**Wave:** SPIKE (timeboxed PROBE, ~30 min) · **Date:** 2026-06-15
**Method:** throwaway micro-charts + stub-host driver, run against the **live `mplv2`** package via the
WSL2 tool-venv `mpl` (no LLM, no Docker, no API spend). Probe code lived in `_spike/` and was deleted
after this writeup (nWave spike discipline: throwaway code, permanent findings).

> **Path note.** Standard nWave puts this at `docs/feature/{id}/spike/findings.md`. `mpl_harness` is not a
> feature-delta feature, so per the repo's single-file convention the findings live where the work lives.

## Assumption tested

`terminal-bench/mpl_harness/design.md`'s chart sketch depends on three MPL constructs. Do they behave as
drawn against the live package?

1. **Seeded weighted-stochastic selection** — `choose(1){ @weight(expr) => … }` where the *same* `SIM/seed`
   yields the *same* draw and weights bias the pick. (The §6 pass@k-diversity + determinism claim.)
2. **`@priority` preemption** — a high-priority guard transition (incl. the multi-source `S1|S2|… when … =>`
   form) wins over a competing normal transition in the **same tick**. (The §3 Abort/HALT guarantee.)
3. **write-var-in-`then` / read-in-guard-next-tick** — a var written in a transition's `then {}` is committed
   and readable on the next tick. (The §3 Verify→Checked once-then-branch gate.)

## Verdicts

| # | Construct | Verdict | Evidence |
|---|---|---|---|
| 1 | `choose(1){@weight}` seeded weighted-random draw | **DOESN'T WORK (as drawn)** | weights **1:3** and **1:99** both gave an exact **50/50** split (`a=39, b=39`); `seed=7` ≡ `seed=42` (identical `(39,39)`). Weight-insensitive **and** seed-independent → not stochastic, not weighted, under `SIM/seed` alone. |
| 2 | `@priority(100)` preempts a normal transition same tick | **WORKS** | From `Work`, a normal `=> Normal` and a `@priority(100) … => Halt` were both enabled; `Halt` won (`picked=2`). Multi-source form confirmed in `stopwatch.mpl`: `@priority(10) Running\|Paused\|Idle when ctrl/RESET => Idle`. |
| 3 | write-in-`then` / read-next-tick | **WORKS** | `picked` written in a `then {}` was committed and read back across ticks. Also already proven by the v1 cage (`obs`/`cmd`/`finished`). |

**Bonus finding — randomness in MPL is host-supplied, not a chart builtin.** `arena.mpl` (the "demonstrates
`rand()`" example) actually imports `randint(lo:int, hi:int) -> int` as a **host function** and calls it from
`then` actions. There is no chart-level seeded RNG engaged by `@weight`. Whatever bias the
`weighted_behavior.mpl` example shows comes from its **changing var values over time** (deterministic drift),
not from a random draw.

## Why construct 1 fails — and why that's fine

`@weight` with constant weights, driven only by `SIM/seed`, resolves **deterministically** (our probe got a
fixed A,B,A,B alternation regardless of weight magnitude or seed). MPL delegates randomness to the **host** —
exactly where harebrain's determinism-given-seed already lives (`fast LLM brain × structured game-AI cage`,
the cage seeded by the harness). So the assumption was wrong about the *mechanism*, not about the *capability*.

## Design implications (these override the prior §6 assumptions)

- **§6 part (a) — "seeded stochastic = free pass@k diversity": REWRITE THE RNG SOURCE.** Do **not** rely on
  `choose(1){@weight}` for randomness. Implement the stochastic policy as a **host-seeded RNG import**, e.g.
  `rand01() -> float` (or `draw(p:float) -> bool`) backed by `random.Random(trial_seed)` in `mpl_agent_v2.py`.
  Feed it into guards: `Decide when rand01() < p_scout => Scout`, or into `@priority(host_score(...))`. The
  harness owns the seed per trial → genuine, replayable pass@k diversity. This is *more* aligned with the
  harebrain model than the chart-RNG idea, not less.
- **§6 part (b) — learned transition probabilities: SURVIVES UNCHANGED.** It already put the probabilities in
  the host (persisted, offline-tune-and-freeze / online-logged+seeded). The host RNG above reads those
  probabilities. No change needed beyond pointing it at the host RNG.
- **§3 Abort HALT guard (`@priority(100)` multi-source guard): BUILD AS DRAWN.** Validated.
- **§3 Verify→Checked once-then-branch gate: BUILD AS DRAWN.** Validated.

## Constraints discovered

- MPL has **no chart-level seeded RNG** reachable from `@weight`. Any stochasticity in `terminal_v2.mpl` must
  come through a **host import**, and reproducibility is the *host's* responsibility (`random.Random(seed)`).
- `choose(n){@weight}` is still usable for **deterministic** prioritized selection (it behaves like an ordered
  pick), just not for randomized selection. Don't use it where §6 wanted entropy.
- `default machine` + `ENTER => …` auto-activates (v1 path); non-`default` machines (e.g. `weighted_behavior`)
  need explicit instantiation — keep `terminal_v2.mpl` on the `default machine` path.

## Net verdict

**2 of 3 constructs WORK as drawn; 1 fails but is cleanly salvageable via a host-seeded RNG.** `terminal_v2.mpl`
is expressible as designed **once §6's randomness moves from `@weight` to a host import.** No blocker to
building the walking skeleton (verify gate + Abort guard first); the stochastic-policy region waits on the
host-RNG rewrite.
