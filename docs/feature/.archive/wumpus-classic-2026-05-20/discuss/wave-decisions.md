# Wave Decisions: wumpus-classic (DISCUSS)

Decisions resolved by the user during the DISCUSS scoping checkpoint. Recorded here so DESIGN, DISTILL, and DEVELOP waves have ground truth.

## Decision 1 — Package location

**Chosen:** `python/packages/wumpus_classic/`

**Alternatives considered:** `wumpus/src/wumpus_classic/` (Luna's initial recommendation, simpler for a single-purpose repo).

**Rationale:** User wants the workspace-member layout consistent with the broader `harebrain` Python monorepo conventions. Future packages (`mplv2`, `harebrain` engine itself) will sit alongside.

**Downstream implication (DESIGN must resolve):** Cells A–G live in `wumpus/experiments/`. They will need to import the engine across project boundaries — either workspace dependency in a parent `pyproject.toml`, editable path install, or `uv workspaces` member declaration. **Does not block DISCUSS.** Flag for solution-architect.

## Decision 2 — RNG fidelity stance

**Chosen:** Single mode: `Game(seed: int | None = None)`. `seed=None` → OS entropy. Experiments pass an explicit `int`. Seed printed in transcript header for self-describing replay.

**Alternatives considered:**
- (a) Bit-exact Microsoft GW-BASIC LCG reproduction. Rejected: high implementation cost, the BASIC source itself doesn't `RANDOMIZE` so there's no canonical "Yob seed" anyway.
- (c) Dual-mode `Game(seeded=True/False)`. Rejected per user: "simplest implementation."

**Implication for AC:** Determinism property = "given the same seed, two `Game` instances produce byte-identical event streams across N≥50 turns." Not "matches PC-BASIC byte-for-byte."

## Decision 3 — Yob's win/lose message swap

**Chosen:** Replicate as-is. Document as Yob-original behavior (game `BAS` lines 0490-0550).

- Win (arrow hits wumpus): `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!`
- Loss (eaten / pit / arrows exhausted): `HA HA HA - YOU LOSE!`

**Rationale:** Fidelity. The swap is the game; players who recognize it recognize the 1973 game.

## Decision 4 — Surface split

**Chosen:** Engine API + thin CLI renderer (option b).

**User's use case (verbatim):** "run experiments where I monitor events and telemetry while a user is playing a game."

**Architecture (binding for DESIGN):**
- Engine always emits structured events to a configurable sink.
- Sink is fan-out capable (e.g., tee to JSONL file + in-memory queue + CLI renderer).
- CLI is a *thin renderer* — its only inputs are the event stream and `stdin`.
- Harness consumers read the same event stream the CLI renders from, concurrently, without altering player-visible output.

**Mandatory AC clause:** "While a human plays via CLI, a harness can capture the full event stream from the same session without altering player-visible output."

## Risk: DISCOVER and DIVERGE were skipped

No `docs/product/discover/` or `docs/feature/wumpus-classic/diverge/recommendation.md` exists. The job statement, persona definitions, and design direction were synthesized by Luna from `wumpus/docs/wumpus_idea.md` and the accompanying experiment notes.

**Mitigation:**
- Jobs in `docs/product/jobs.yaml` marked `validation: synthesized-from-informal-notes`.
- Both personas (Player Pat, Harness Harriet) are grounded directly in `wumpus_idea.md` paragraphs that describe them ("trusted narrator" → Pat-shaped expectations; "oracle replay" → Harriet-shaped expectations).
- If later interviews invalidate either persona, the corresponding journey/stories require re-validation. Stories carry a `validation: synthesized` flag.

## Risk: Cross-package imports for experiments

Cell A–G code in `wumpus/experiments/` will import from `python/packages/wumpus_classic/`. Solution depends on the workspace tool chosen by DESIGN. Options for DESIGN to weigh:

1. `uv workspaces` member at repo root with `python/packages/wumpus_classic` and `wumpus/` both as members.
2. Editable install (`pip install -e python/packages/wumpus_classic`) from `wumpus/.venv/`.
3. Path-based import (`sys.path` injection in experiment runners) — least clean, possibly fine for spike work.

**Not a DISCUSS blocker.** Flagged for handoff.

## Scope Assessment: PASS

7 user stories | 1 bounded context (the engine package) + 1 surface (CLI renderer) | walking skeleton touches 4 integration points (engine, event sink, CLI renderer, parser) | estimated 8-12 days end-to-end | single user outcome ("play and instrument classic Wumpus").

Right-sized. No splitting required.

## Changelog

- 2026-05-20: Initial decisions captured after scoping checkpoint with user.
