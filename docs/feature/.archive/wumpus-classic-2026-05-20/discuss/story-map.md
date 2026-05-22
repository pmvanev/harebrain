# Story Map: wumpus-classic

## Users: Player Pat, Harness Harriet
## Goal: Play and instrument Yob's 1973 Hunt the Wumpus with byte-recognizable fidelity

## Backbone

| 1. Start a game | 2. Orient | 3. Choose action | 4. Resolve action | 5. Reach terminal state | 6. Replay |
|---|---|---|---|---|---|
| `wumpus` runs | senses + room + tunnels | `S` or `M` | move / shoot resolution | win/lose + SAME SET-UP prompt | `Game(seed=42)` reproduces session |
| `Game(seed=...)` | adjacency listed | (engine emits `PromptIssued`) | (engine emits `ActionChosen`+resolution events) | (engine emits `GameEnded`) | event stream byte-identical to recording |

### Walking Skeleton (Slice 1)

The thinnest end-to-end slice that connects all activities. No hazards, no wumpus, no arrows. Just movement on the dodecahedron.

| Activity | Skeleton task |
|---|---|
| 1. Start | `wumpus` launches; engine constructs with cave layout BUT no wumpus, no pits, no bats — player only |
| 2. Orient | Print `YOU ARE IN ROOM <n>` and `TUNNELS LEAD TO <a> <b> <c>` (no sense lines because no hazards exist) |
| 3. Choose | Prompt `SHOOT OR MOVE (S-M)?`; accept only `M` (S is unimplemented in skeleton — print `NOT YET` placeholder is forbidden; instead, `S` re-prompts) |
| 4. Resolve | `WHERE TO?` accepts adjacent room or current room; move resolves; loop back to Orient |
| 5. Terminal | Ctrl-C triggers `SessionAborted` event; engine exits cleanly. No "you win / lose" yet because no hazards. |
| 6. Replay | `Game(seed=42)` with a recorded move sequence emits the same event stream |

**Walking skeleton validates:**
- the prompt/parse/respond cycle works
- the dodecahedron graph is correct
- the event sink fan-out works (CliRenderer + JsonlSink concurrently)
- determinism under seed even on a hazardless game

**Walking skeleton explicitly does NOT validate:**
- any combat rule (wumpus startle, arrow physics, bat teleport, pit death)
- any Yob outcome message (the famous swap)
- rule-fidelity coverage

This is intentional. The skeleton is the thinnest slice — combat rules layer on top in Slices 2 and 3.

### Ribs (full task list per activity)

```
1. Start                  2. Orient            3. Choose          4. Resolve            5. Terminal       6. Replay
----------               ----------            ----------         ----------            ----------        ----------
launch (CLI)              YOU ARE IN ROOM      SHOOT OR MOVE?     move (legal target)   game over flag    seed in header
construct (engine)        TUNNELS LEAD TO      reject invalid     reject illegal move   HEE HEE HEE       byte-identical replay
seed handling             I SMELL A WUMPUS     ----------         move to current room  HA HA HA          observer-effect absent
INSTRUCTIONS prompt       I FEEL A DRAFT       NO. OF ROOMS?      ----------            SAME SET-UP=Y     concurrent sink fanout
cave gen (entities)       BATS NEARBY          ROOM #?            wumpus bump            SAME SET-UP=N
crossover re-roll         ----------           ARROWS AREN'T      pit fall              ----------
HUNT THE WUMPUS banner    sense for all adj.    THAT CROOKED      bat teleport          SessionAborted
----------                strict L-array order ----------         bat -> hazard chain
transcript header                                                  ----------
                                                                   arrow walk
                                                                   arrow random tunnel
                                                                   arrow hit wumpus
                                                                   arrow hit self
                                                                   arrow miss
                                                                   wumpus startle on miss
                                                                   wumpus startle onto player
                                                                   arrow count decrement
                                                                   out-of-arrows -> lose
```

## Release slices

### Slice 1 — Walking Skeleton (US-01, US-02)

**Tasks:**
- US-01 Engine boots with seeded cave and emits structured events
- US-02 CLI loop runs end-to-end with movement-only gameplay

**Outcome KPI targeted:** "walking skeleton runs" — `Game(seed=42)` with a 10-move all-movement command sequence produces identical events on replay.

**Rationale:** Validates the engine-with-sinks architecture, the parser, and the dodecahedron. If this slice doesn't ship, everything else is gated on a broken foundation.

### Slice 2 — Senses and hazards (US-03)

**Tasks:**
- US-03 Hazards (wumpus, bats, pits) populate cave; senses emit on entry; walking-into-hazard ends or teleports

**Outcome KPI targeted:** rule-fidelity coverage for the passive game elements — every Yob rule in lines 2000-2150 (senses) and 4140-4310 (hazard resolution on move) has at least one acceptance scenario.

**Rationale:** Adds the entire passive ruleset (senses, walking-into-hazards) before the active ruleset (shooting). This is one demoable behavior class — Pat can lose in a hazard but cannot yet hunt the wumpus.

### Slice 3 — Arrows and shooting (US-04)

**Tasks:**
- US-04 Shooting works end-to-end: path entry, validation, walk, hit/miss, wumpus startle, self-shot, arrow count, out-of-arrows loss, Yob's swapped win/lose messages

**Outcome KPI targeted:** rule-fidelity coverage for the active ruleset — every Yob rule in lines 3000-3440 has at least one acceptance scenario. Also: Yob message-swap byte-equality test passes.

**Rationale:** Completes the game. After this slice, Pat can play a full game start-to-end-state. This is the largest slice (most rules, most edge cases) but cannot be split smaller without breaking the "demoable in a session" criterion — half-shooting is no shooting.

### Slice 4 — Determinism and instrumentation (US-05, US-06)

**Tasks:**
- US-05 Seeded replay produces byte-identical event streams
- US-06 Concurrent CLI + JSONL sink — observer-effect absent

**Outcome KPI targeted:** Harriet's KPIs — replay-determinism (byte-identical over N=20 seeded runs of 50 turns), concurrent-monitoring contract (CLI stdout identical with/without sink attached).

**Rationale:** Slice 1's walking skeleton already proves the architecture works; Slice 4 hardens it to harness-grade. The acceptance bar moves from "it runs" to "it runs the same way every time, even when observed."

### Slice 5 — Fidelity audit harness (US-07)

**Tasks:**
- US-07 Oracle-parity comparison: engine event stream vs. `pcbasic wumpus.gwbasic.bas` driven via `wexpect`

**Outcome KPI targeted:** oracle-parity (N=10 hand-curated scenarios match PC-BASIC byte-for-byte modulo seed mapping); rule-coverage closure (all rules from the Yob audit doc have at least one acceptance test).

**Rationale:** External validation. The engine could be self-consistent and still drift from Yob; only diffing against the BASIC reference catches that. This slice produces the evidence for the "byte-recognizable fidelity" claim in the vision.

## Priority Rationale

Slice order is determined by outcome dependency:

1. **Slice 1 must come first** because every later slice's acceptance scenarios depend on a working engine-CLI loop. Riskiest assumption: "engine-with-sinks architecture supports both Pat and Harriet without mode-switching" — validate by building it.

2. **Slice 2 before Slice 3** because shooting (Slice 3) requires the wumpus, bats, and pits to exist and behave correctly (Slice 2 dependency: HazardTriggered events must fire correctly before arrow startles can be tested). Movement-and-hazards is also a smaller, demoable behavior — useful checkpoint.

3. **Slice 3 completes the game** before Slice 4 hardens it. Reasoning: a fully playable but slightly nondeterministic engine is still demoable; a perfectly deterministic engine with no shooting is not. Slice 3 unblocks the demo; Slice 4 unblocks Harriet.

4. **Slice 4 before Slice 5** because the oracle harness (Slice 5) needs deterministic replay (Slice 4) to compare against PC-BASIC traces. Without seeded determinism, every PC-BASIC vs engine diff would have a confound: "is this a fidelity bug or a seed-drift artifact?"

5. **Slice 5 last** because it is the validation layer, not the product. It produces evidence for the fidelity claim but does not add features Pat or Harriet directly use.

**Tie-breaking (Walking Skeleton > Riskiest Assumption > Highest Value):** Slice 1 is the skeleton. After that, the riskiest assumption is "the same engine can serve Pat and Harriet without compromise." Slices 2-4 progressively de-risk this. Slice 5 is highest verifiable value (gives the fidelity claim its evidence) but lowest urgency.

## Out of scope (this feature)

- WUMP2 cave variants (different topology) — separate feature
- WUMP3 hazard variants — separate feature
- Escalation-ladder L2 (wumpus moves on its own) — separate feature
- MPL chart of the same rules — separate feature, separate package
- LLM player implementations — separate features (cells D, E, F)
- Wild baseline cell G — already exists outside this package

## Notes for downstream waves

- Story IDs are pinned in `user-stories.md`.
- Walking skeleton scope is intentionally narrower than US-01 alone — the skeleton is a *behavior slice* (movement-only), while US-01 covers the full Slice 1 behavior (boot + event emission). DESIGN may sequence US-01 as multiple sub-tasks to land the skeleton incrementally.
