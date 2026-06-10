# Mutation-testing exemptions (equivalent / unkillable mutants)

Per CLAUDE.md § Mutation Testing Strategy: surviving mutants either get a killing
test in the same slice or a documented exemption here. Exempted mutants are
**excluded from the kill-rate denominator** (kill rate = killed / (total − exempted)).

An exemption is justified only when the mutant is a *genuinely equivalent* mutant —
it produces no observable behavioural change at the port boundary, so any test that
"kills" it would be asserting a language guarantee or source-shape detail (a banned
anti-pattern per `nw-test-optimization` SKILL §2), not a domain behaviour.

---

## R5-S01 — `src/wumpus/host_import.py` (2026-06-10)

| # | Location | Operator | Mutation | Justification |
|---|----------|----------|----------|---------------|
| 1 | `host_import.py:32` | `core/ReplaceTrueWithFalse` | `@dataclass(frozen=True)` → `@dataclass(frozen=False)` on `StepResult` | **Equivalent.** `frozen=` only governs *post-construction attribute reassignment*. `StepResult` is constructed once inside `step_from_snapshot` and returned; no code path (production or test) ever reassigns an attribute on an instance, so the immutability flag has zero observable effect at the driving-port boundary. Killing it would require `with pytest.raises(FrozenInstanceError): result.events = []` — a Python language-guarantee / dataclass-field-semantics assertion, explicitly banned by `nw-test-optimization` SKILL §1.2 ("Internal data shape — dataclass field assignment — language guarantees") and §2.3 (Trivial Dataclass-Storage Tests). Excluded from the denominator. |

**Note (tooling, not an exemption):** the `core/RemoveDecorator` mutant on the same
line was initially reported `INCOMPETENT` due to a cosmic-ray Windows bug — when the
mutated test run fails (i.e. the mutant is caught), `cosmic_ray/testing.py:51` calls
`err.output.decode("utf-8")` on pytest output containing a cp1252 byte (0x97, the `—`
em-dash in assertion messages) and crashes before recording `KILLED`. Running
cosmic-ray with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` in the environment forces the
test subprocess to emit UTF-8, after which the mutant reports cleanly as `KILLED`.
This is a *tooling* workaround, not a code or test exemption — re-run the R5 session
with those two env vars set to reproduce the clean result.
