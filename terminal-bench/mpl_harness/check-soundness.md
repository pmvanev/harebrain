# check() soundness — the verify gate's design (Risk #1)

**Status:** DESIGN (no spend) · **Date:** 2026-06-15 · **Feeds:** `mpl_agent_v2.py`'s `check()` and a
chart amendment to `terminal_v2.mpl`. Resolves the open question flagged in `design.md` §1/§3 and Risks.

> The verify gate (`design.md` §1, the accuracy-first lever) is only worth its ticks if `check()` is **sound**.
> The skeleton (`terminal_v2.mpl`) wires the gate; this note decides what `check()` may and may not do, grounded
> in the *actual* TB task structure inspected locally (`terminal-bench-core==0.1.1`, 80 tasks).

## What the agent can observe vs. what is hidden

Inspected a representative task (`hello-world`) and two contrasting ones (`openssl-selfsigned-cert`,
`prove-plus-comm`). Every task has the same shape:

| File | Visible to the agent during its run? |
|---|---|
| `task.yaml` → `instruction` | **YES** — this is the prompt. |
| the live terminal / container filesystem | **YES** — the agent's own end-state. |
| `solution.sh` (reference solution) | **NO** — never in the container. |
| `tests/test_outputs.py` (the grader) | **NO — injected only at grading time.** |

**The decisive fact (confirmed, not assumed).** The task `Dockerfile` is just
`FROM …/python-3-13` — it does **not** `COPY tests/`. `docker-compose.yaml` runs the container as
`sleep infinity` and passes `TEST_DIR=${T_BENCH_TEST_DIR}` as a harness-filled env var; `run_tests_in_same_shell:
false`. The grader (`setup-uv-pytest.sh` → `run-uv-pytest.sh` → `tests/test_outputs.py`) is copied into
`$TEST_DIR` and run **after** the agent session ends, in a fresh shell. So during the run, the oracle is
**physically absent** from the container.

**Two consequences, one conclusion:**
1. `check()` **cannot** run the hidden grader — it isn't there.
2. Even if it could, doing so would **leak the oracle** (the integrity bar / canary string forbid it) and would
   be gameable — the brain grading against the exact exam it's being scored on.

→ **The only sound `check()` re-derives the task's success condition from the *public instruction* and asserts
it against the *real* end-state, deterministically.**

## The soundness rule, applied

From `design.md` §1 (the two-clock / soundness rule): a **deterministic check is sound**; an **LLM judgment is
advisory** (unsound). Applied to `check()`:

- ✅ **Sound:** a shell predicate over the real container state that returns a real **exit code** —
  `test -f /app/ssl/server.key`, `stat -c %a … = 600`, `openssl rsa -in … -noout`, `coqc plus_comm.v`,
  `./prog < sample | diff - expected`. The verdict is the exit code, not an opinion.
- ❌ **Unsound:** "the screen looks like it worked" / the model answering "yes I'm done." This is exactly the
  intrinsic-self-correction failure the research warns about (README §1/§2: self-correction 95.5→89.0;
  CRITIC needs *external* tools). Self-judgment as the gate's verdict re-introduces the failure the gate exists
  to remove.
- ❌ **Off-limits:** reading `$TEST_DIR`, `tests/`, or `solution.sh`. Sound in form, but it's the oracle.

## The design — a separate verifier pass that authors an observable predicate

At done-time (the brain's first `__DONE__`), the cage does **not** trust the claim. It runs a **verifier pass
that is separate from the solver's context**:

1. A fresh prompt — *not* the solver's running transcript — receives the **public instruction** + a snapshot of
   the **observable end-state** (relevant `ls`/`cat`/`stat` output the host gathers).
2. It emits a single **bash predicate** that exits `0` iff the instruction's *observable* requirements hold.
3. The host runs that predicate through the same exec path as `act()`. `check()` returns `(exit code == 0)`.

Why **separate** verifier (not the solver checking itself): a solver asked "are you done?" rationalizes its own
work — correlated error. A verifier grounded **only** in the instruction + observed state, with no stake in the
prior plan, is decorrelated and closer to how the human test author worked from the same spec. (This is the
"tool-grounded / external-signal" stance from README §1; the solver/verifier split is the cheap structural way
to get it.) Generalizes across all 89 tasks — **no per-task host code**, because the predicate is derived per
task from its own instruction.

## The asymmetry — what a verdict means (and the coverage spectrum)

`check()` is a **sound lower bound**, not the oracle:

- **A `check()` FAILURE is a real, observable deficiency** — a named file is missing, a command errors,
  `coqc` won't compile, output mismatches. The gate is *right* to send the solver back. This is the high-value
  direction: it kills the premature-`done` class directly (recall TB-2's **24.1% command-not-found** failures).
- **A `check()` PASS is necessary, not sufficient** — the observable predicate held, but the hidden grader may
  assert more.

Coverage of a PASS varies by task:

| Task type | Example | Observable coverage of a PASS |
|---|---|---|
| File/config/security, fully-enumerated spec | `openssl-selfsigned-cert`, `hello-world` | **Strong** — instruction lists exact paths/perms/fields; predicate ≈ grader. |
| Build / compile / "the program runs" | `prove-plus-comm` (coqc exit 0, no `admit`), `fibonacci-server` | **Strong** — success is an exit code, fully observable. |
| Hidden-input / hidden-expected-output, tolerance-graded | `swe-bench-*` (hidden suite), `raman-fitting`, `path-tracing` | **Weak** — the grader uses inputs/answers not in the instruction; predicate catches only gross failures. |

## Consequence: a chart amendment (the skeleton's unbounded loop is wrong)

The walking skeleton loops `Checked when !verified => Perceive` **unboundedly** until the budget HALTs. The
soundness analysis shows that's a *new* failure mode: an over-strict or simply *wrong* verifier predicate would
trap an actually-correct solution and burn the whole budget to an Abort — converting a pass into a fail. Since a
PASS is necessary-not-sufficient **and** the predicate can be wrongly-strict, the gate must be **bounded** and
must **defer to the grader** on exhaustion:

```
vars { verify_fails:int := 0; max_verify_fails:int := 2; }

Verify  => Checked then { verified := check(); };
Checked when verified                                       => Done     then { finished := true; };
Checked when !verified && verify_fails <  max_verify_fails  => Perceive then { verify_fails += 1; };
Checked when !verified && verify_fails >= max_verify_fails  => Done     then { finished := true; };  // SUBMIT, let the real grader decide
```

Rationale for **submit-on-exhaustion** (not Abort): when retries run out we don't know whether the solver or the
verifier is wrong. Submitting lets the *sound* external grader adjudicate; self-Aborting throws away a possibly
correct solution. The `@priority(100)` budget rule stays as the outer backstop for genuine spin (e.g. a solver
that never claims done). Net: the gate kills premature-`done` **without** introducing a verify-trap failure.

## What this means for `mpl_agent_v2.py`

- Add a 4th host leaf `check() -> bool`, implemented as: gather observable state → **separate verifier LLM call**
  → emit bash predicate → run via `session.send_keys` / exec → return exit-code==0. Never touch `$TEST_DIR`.
- The verifier prompt is distinct from `decide()`'s solver prompt (decorrelation).
- Count verifier tokens separately so the gate's cost is measurable against the accuracy it buys (priority #2).

## Residual risk (honest limits)

- **Weak-coverage tasks** get only a gross-failure filter from the gate; their accuracy still rests on the
  solver. That's acceptable — the gate never *hurts* there (bounded + submit-on-exhaustion), it just helps less.
- **A wrong predicate** still costs up to `max_verify_fails` extra cycles. Keep the cap small (2) and the
  verifier prompt tight ("assert only what the instruction explicitly requires; do not invent requirements").
- **Verifier cost** is real (one extra call per done-claim). Justified only because premature-`done` is a top
  failure class; if metrics show it isn't earning its tokens, gate it behind a cheap pre-check.
