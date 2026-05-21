<!-- markdownlint-disable MD024 -->
# User Stories: wumpus-classic

## System Constraints

Cross-cutting constraints that apply to every story below. DESIGN must honor; DEVELOP must enforce; DISTILL must test.

- **C-1 Yob fidelity:** the visible CLI surface — prompts, sense lines, location/tunnel printing, outcome messages, the win/lose message swap — must be byte-identical to `wumpus/experiments/g_wild_baseline/wumpus.gwbasic.bas`. Any deviation is a bug, not a "modernization."
- **C-2 Single RNG source (Decision 2):** every random draw inside the engine must come from a single `random.Random` instance constructed at `Game(seed=...)` time. Module-level `random.*` calls, `os.urandom`, `time.time()`, or any other entropy source in engine code paths are forbidden.
- **C-3 Observer-effect absence (Decision 4):** sink subscription must not alter event emission order, count, or payload. CLI stdout must be identical whether zero or N sinks are attached.
- **C-4 Event schema as API:** the event types and field names in `wumpus_classic.events` are a published API contract. Breaking changes require a version bump.
- **C-5 Pure engine, thin renderer:** the engine package depends only on the Python standard library and the events module. The CLI renderer is a separate module that takes events and stdin and emits stdout — no engine logic in the renderer.
- **C-6 GameEnded is terminal:** no event may be emitted after `GameEnded` for the same game session. `SAME SET-UP (Y-N)?` starts a *new* session.
- **C-7 No mocks of engine in CLI tests:** CLI tests drive the real engine via stdin and observe real stdout. Faking the engine defeats the integration value of the test.

## Impacted Journeys

- `docs/feature/wumpus-classic/discuss/journey-play-classic-wumpus.yaml` (the only journey for this feature)
- `docs/feature/wumpus-classic/discuss/journey-play-classic-wumpus-visual.md`

---

## US-01: Engine boots with seeded cave and emits structured events

### Elevator Pitch

- **Before:** A researcher who wants to use Hunt the Wumpus as an oracle has no Python implementation; they install PC-BASIC into a Python 3.12 tool environment, run BASIC, and screen-scrape stdout. Reproducibility requires hand-editing a `RANDOMIZE` line into BASIC source.
- **After:** A researcher runs `Game(seed=42)` in Python, receives a `Snapshot` and an `EventBus` to subscribe to. The first event in the stream is `GameStarted(seed=42, layout_hash=..., snapshot=...)`. Reproducibility is one constructor argument.
- **Decision enabled:** the researcher can decide whether to attach a `JsonlSink`, a queue sink, or no sink — and can decide which seeded scenarios to enumerate for downstream cells.

### Job

`job_id: instrument-wumpus-play`

(Secondary: `replay-wumpus-deterministically` — covered more specifically in US-05.)

### Problem

Harness Harriet is a researcher who needs an in-process, seedable Hunt the Wumpus to use as an oracle for LLM-player experiments. She finds it painful to install and screen-scrape PC-BASIC, and the BASIC source has no seeding hook short of source modification. The only Python Wumpus implementations she has found are unseeded or undocumented in their event schema, so she cannot diff agent claims against a ground truth she trusts.

### Who

- **Harness Harriet** — researcher running LLM-player experiments
- **Context:** scripting experiment harnesses that need ground-truth oracles for divergence-event measurement
- **Motivation:** trusts measurements only when the oracle is independently auditable and seedable

### Solution

A `Game(seed: int | None = None)` constructor that places the wumpus, two pits, two bats, and the player into a fixed 20-room dodecahedron, resolves entity crossovers (Yob lines 0240-0340), and emits `GameStarted` containing the seed, a layout hash, and an initial snapshot.

### Domain Examples

#### 1: Happy Path — Harriet instantiates with a specific seed

```python
from wumpus_classic import Game
game = Game(seed=42)
events = []
game.events.subscribe(events.append)
# After construction, events contains exactly one event:
assert events[0].kind == "GameStarted"
assert events[0].seed == 42
assert events[0].snapshot.player_room in range(1, 21)
```

#### 2: Edge Case — Harriet instantiates without a seed

```python
game = Game()  # seed=None -> OS entropy
assert game.seed is not None  # engine drew a seed
assert isinstance(game.seed, int)
# game.seed is printable for self-describing transcripts
```

#### 3: Edge / Error — Cave generation forces re-roll on crossover

For some seeds, the initial draw of 6 room positions produces collisions (e.g., wumpus and pit1 in the same room). Per Yob lines 0290-0340, the engine re-rolls all 6 positions until no two are equal. The visible result: `Snapshot.layout` always has 6 distinct rooms, regardless of seed.

```python
game = Game(seed=1)
layout = game.snapshot().layout
positions = [layout.player_start, layout.wumpus_room, layout.pit1, layout.pit2, layout.bat1, layout.bat2]
assert len(set(positions)) == 6
```

### UAT Scenarios (BDD)

#### Scenario: Engine boots with a seed and emits the start event

```gherkin
Given Harriet imports Game from wumpus_classic
When Harriet calls Game(seed=42)
Then a single GameStarted event is emitted
And the GameStarted event contains seed=42
And the GameStarted event contains a snapshot with 6 distinct entity positions
And the GameStarted event contains a layout_hash deterministic in the seed
```

#### Scenario: Engine boots without a seed and self-seeds

```gherkin
Given Harriet imports Game from wumpus_classic
When Harriet calls Game() with no arguments
Then the engine draws a seed from OS entropy
And the drawn seed is exposed as Game.seed
And the GameStarted event contains the drawn seed
```

#### Scenario: Two instances with the same seed have identical layouts

```gherkin
Given Harriet has called Game(seed=42) twice
Then both instances' snapshots have identical wumpus, pit, bat, and player positions
And both instances' layout_hash values are equal
```

#### Scenario: Cave generation eliminates entity crossovers

```gherkin
Given Harriet has called Game(seed=<any seed in a 100-seed grid>)
Then the player_start, wumpus_room, pit1, pit2, bat1, bat2 are all distinct rooms
```

#### Scenario: Sink subscription before construction not required

```gherkin
Given Harriet wants to capture all events including GameStarted
When Harriet subscribes a sink after Game(seed=42) returns
Then the sink can read GameStarted from the EventBus replay buffer
# Implementation note for DESIGN: EventBus retains a replay buffer at least until the first step() call
```

### Acceptance Criteria

- [ ] AC-01.1 — `Game(seed=int)` is deterministic in `seed`: two instances produce equal `layout_hash`.
- [ ] AC-01.2 — `Game()` with no args draws a random seed and exposes it as `Game.seed`.
- [ ] AC-01.3 — `GameStarted` event is emitted exactly once per game session, before any other event.
- [ ] AC-01.4 — Cave layout has 6 distinct entity positions for every valid seed.
- [ ] AC-01.5 — No `import random` at module scope; no `os.urandom`; no `time.time()` in engine paths. (Code-search gate.)

### Outcome KPIs

- **Who:** Harness Harriet
- **Does what:** instantiates the engine programmatically with a seed and receives a reproducible cave layout via a structured event
- **By how much:** 100% of seeded instantiations produce identical layouts on repeat (replay determinism)
- **Measured by:** unit test asserting equality of `layout_hash` and `Snapshot` for two `Game(seed=42)` instances
- **Baseline:** None (greenfield)

### Technical Notes

- Constraints: C-2 (single RNG), C-4 (event schema as API).
- Dependencies: none upstream; US-02 depends on this story.
- Estimated effort: 2 days. (Cave gen + crossover re-roll + event bus + GameStarted event + tests.)
- Right-sized: 5 scenarios, 2 days, single demoable behavior.

### Story Size

2 days | 5 scenarios | demoable as: "I can `Game(seed=42)` in a REPL and inspect the snapshot."

---

## US-02: CLI loop runs end-to-end with movement-only gameplay (walking skeleton)

### Elevator Pitch

- **Before:** Pat cannot run a Python Hunt the Wumpus. There is no `wumpus` command on her PATH.
- **After:** Pat types `wumpus` at her terminal and is dropped into a 20-room dodecahedron. She sees `YOU ARE IN ROOM 8`, `TUNNELS LEAD TO 1 7 9`, and can move with `M 7`. There are no hazards yet — just the cave geometry and the movement loop. Ctrl-C exits cleanly.
- **Decision enabled:** Pat can verify the cave geometry and the prompt/parse cycle feel like Yob before any combat rules ship. She can also tee the session to a JSONL transcript with `--transcript=session.jsonl`.

### Job

`job_id: play-classic-wumpus`

### Problem

Pat is a 1973-game enthusiast who wants to verify that the Python port's prompt/parse cycle, room numbering, and adjacency match Yob before trusting it with the harder rules. She finds it painful to debug a finished engine where prompt fidelity bugs are hidden inside combat rule bugs. She wants to validate the foundation first.

### Who

- **Player Pat** — 1973-game enthusiast at a terminal
- **Context:** first install; wants to kick the tires before trusting the full engine
- **Motivation:** the cave geometry and prompt cycle are the foundation; bugs there poison everything else

### Solution

A `wumpus` CLI command that boots the engine in *skeleton mode* (no wumpus, no pits, no bats — just the player on the dodecahedron), prints `HUNT THE WUMPUS`, prompts `SHOOT OR MOVE (S-M)?`, and loops on `M <room>` movement. `S` re-prompts (skeleton has no shoot logic). Ctrl-C emits `SessionAborted` and exits with code 0.

(In production, skeleton mode is gated by an internal `--no-hazards` debug flag — not exposed to Pat by default. The shipping CLI runs with hazards on. The walking skeleton *as a slice* delivers the underlying engine+CLI loop, which the shipping CLI inherits.)

### Domain Examples

#### 1: Happy Path — Pat plays a 5-move session and quits

```
$ wumpus --no-hazards --seed 42
INSTRUCTIONS (Y-N)? N
HUNT THE WUMPUS
YOU ARE IN ROOM  8
TUNNELS LEAD TO  1  7  9

SHOOT OR MOVE (S-M)? M
WHERE TO? 7
YOU ARE IN ROOM  7
TUNNELS LEAD TO  6  8 17

SHOOT OR MOVE (S-M)? M
WHERE TO? 17
YOU ARE IN ROOM 17
TUNNELS LEAD TO  7 16 18

SHOOT OR MOVE (S-M)? ^C
$
```

#### 2: Edge — Pat enters an invalid room number

```
SHOOT OR MOVE (S-M)? M
WHERE TO? 99
NOT POSSIBLE -
WHERE TO? 7
YOU ARE IN ROOM  7
```

#### 3: Edge — Pat types `S` in skeleton mode

```
SHOOT OR MOVE (S-M)? S
SHOOT OR MOVE (S-M)?
```

(Skeleton mode re-prompts. In the full game, `S` initiates the arrow path collection per US-04.)

### UAT Scenarios (BDD)

#### Scenario: Pat starts a skeleton session and sees the banner

```gherkin
Given Pat has installed wumpus_classic
When Pat runs "wumpus --no-hazards --seed 42"
Then Pat sees "INSTRUCTIONS (Y-N)?"
And after answering "N", Pat sees "HUNT THE WUMPUS"
And Pat sees the location and tunnels for room 8
```

#### Scenario: Pat moves to an adjacent room

```gherkin
Given Pat is in room 8 with tunnels to rooms 1, 7, 9
When Pat types "M" then "7"
Then Pat sees the location and tunnels for room 7
```

#### Scenario: Invalid move is rejected with NOT POSSIBLE

```gherkin
Given Pat is in room 8 with tunnels to rooms 1, 7, 9
When Pat types "M" then "99"
Then Pat sees "NOT POSSIBLE -"
And the engine re-prompts "WHERE TO?"
And Pat's room is unchanged
```

#### Scenario: Pat moves to current room (Yob permits this)

```gherkin
Given Pat is in room 8
When Pat types "M" then "8"
Then Pat is still in room 8
And the engine prints the location and tunnels for room 8
```

#### Scenario: Ctrl-C exits cleanly with a SessionAborted event

```gherkin
Given Pat is at any prompt
When Pat sends SIGINT (Ctrl-C)
Then the engine emits a SessionAborted event
And the CLI exits with code 0
And no Python traceback is printed
```

#### Scenario: Concurrent JSONL sink captures the session

```gherkin
Given Pat runs "wumpus --no-hazards --seed 42 --transcript /tmp/session.jsonl"
When Pat plays a 3-move session and quits
Then /tmp/session.jsonl contains a header line with seed=42 and the version
And /tmp/session.jsonl contains one JSON line per event, including GameStarted, MoveAttempted, MoveResolved, SessionAborted
And Pat's stdout is byte-identical to the same session run without --transcript
```

### Acceptance Criteria

- [ ] AC-02.1 — `wumpus` command is installed and on PATH after `pip install wumpus_classic`.
- [ ] AC-02.2 — `wumpus --no-hazards --seed N` boots the skeleton engine.
- [ ] AC-02.3 — Pat can move with `M <room>` to any adjacent room or her current room.
- [ ] AC-02.4 — Invalid moves print `NOT POSSIBLE -` and re-prompt.
- [ ] AC-02.5 — `S` in skeleton mode re-prompts (no error message; just re-prompt).
- [ ] AC-02.6 — Ctrl-C exits with code 0, emits `SessionAborted`, prints no traceback.
- [ ] AC-02.7 — `--transcript PATH` writes JSONL transcript without altering stdout (C-3).
- [ ] AC-02.8 — Transcript header line contains `seed=<N>` and version (C-1 / shared artifact: seed).

### Outcome KPIs

- **Who:** Player Pat
- **Does what:** completes an end-to-end CLI session (boot + move + quit) on first install
- **By how much:** 100% of skeleton sessions complete without traceback; 100% of `--transcript` sessions produce byte-identical stdout to non-transcript sessions
- **Measured by:** integration test driving the CLI with stdin scripts; diffing stdouts across transcript/no-transcript runs
- **Baseline:** None

### Technical Notes

- Constraints: C-1, C-3, C-5, C-7.
- Dependencies: US-01 (engine exists; movement-only is a subset of US-01's engine).
- Estimated effort: 2 days.
- Right-sized: 6 scenarios, 2 days, walking-skeleton slice.

### Story Size

2 days | 6 scenarios | demoable as: "I can play a 5-move CLI session and tee the events to disk."

---

## US-03: Hazards, senses, and walking-into-hazards end-state behavior

### Elevator Pitch

- **Before:** Pat plays the skeleton but the cave is empty — no smell, no draft, no bats, no pits, no wumpus. The game is unrecognizable as Hunt the Wumpus.
- **After:** Pat plays a full hazard-populated cave. On entering a room, she sees `I SMELL A WUMPUS!`, `I FEEL A DRAFT`, or `BATS NEARBY!` for each adjacent hazard, in Yob's L-array order. Walking into the wumpus prints `...OOPS! BUMPED A WUMPUS!` and triggers the startle rule. Walking into a pit prints `YYYIIIIEEEE . . . FELL IN PIT` and `HA HA HA - YOU LOSE!`. Walking into a bat prints `ZAP--SUPER BAT SNATCH!` and teleports her — potentially into another hazard, recursively.
- **Decision enabled:** Pat can play hazard-resolution-only games (shooting still re-prompts) and verify the entire passive ruleset is faithful.

### Job

`job_id: play-classic-wumpus`

### Problem

Pat needs the passive ruleset (senses + walking-into-hazard outcomes) to work exactly as Yob's BASIC source dictates. She finds the original's bat teleport memorable specifically because it can chain into another hazard — a "softer" reimplementation that protects the player from bat-into-pit would feel wrong.

### Who

- **Player Pat** — 1973-game enthusiast
- **Context:** wants to play a recognizable game including the harsh rules
- **Motivation:** Yob's brutality is the design; a softened version is not the game

### Solution

Populate the cave with one wumpus, two pits, two bats (placed by US-01's cave gen, no crossovers). Implement sense emission on room entry per `shared-artifacts-registry.md#sense-order` and hazard resolution on move per `#hazard-check-order`. Bat teleport recursively re-enters the destination room (Yob's GOTO 4130) so chains are possible.

### Domain Examples

#### 1: Happy Path — Pat enters a room with three adjacent hazards

Setup: wumpus in room 1, pit in room 7, bat in room 9. Pat enters room 8 (adjacent to 1, 7, 9).

```
YOU ARE IN ROOM  8     (no — order is: senses first, then location/tunnels)
```

Correct expected output:

```
I SMELL A WUMPUS!
I FEEL A DRAFT
BATS NEARBY!
YOU ARE IN ROOM  8
TUNNELS LEAD TO  1  7  9
```

#### 2: Edge — Bat-into-pit chain

Setup: bat in room 5, pit in room 17. Engine's next bat-teleport draw will land Pat in room 17.

```
SHOOT OR MOVE (S-M)? M
WHERE TO? 5
ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!
YYYIIIIEEEE . . . FELL IN PIT
HA HA HA - YOU LOSE!
SAME SET-UP (Y-N)?
```

#### 3: Edge — Wumpus bump that startles to a safe room

Setup: wumpus in room 7. Pat enters room 7 (wumpus's room). Engine's startle roll: K=1 → wumpus moves to S(7,1) = room 6 (safe, not Pat's prev room).

```
SHOOT OR MOVE (S-M)? M
WHERE TO? 7
...OOPS! BUMPED A WUMPUS!
YOU ARE IN ROOM  7
TUNNELS LEAD TO  6  8 17
```

(Game continues. The bump is the only "near-death" event in the game.)

### UAT Scenarios (BDD)

#### Scenario: Pat sees senses in Yob's L-array order

```gherkin
Given the wumpus is in room 1 and a pit is in room 7 and a bat is in room 9
And Pat is entering room 8 which is adjacent to 1, 7, and 9
When Pat moves into room 8
Then Pat sees "I SMELL A WUMPUS!" before "I FEEL A DRAFT"
And Pat sees "I FEEL A DRAFT" before "BATS NEARBY!"
And Pat sees the location and tunnels lines after all sense lines
```

#### Scenario: Pat falls into a pit and loses with Yob's swapped message

```gherkin
Given a pit is in room 4 and Pat is in room 3 adjacent to room 4
When Pat moves to room 4
Then Pat sees "YYYIIIIEEEE . . . FELL IN PIT"
And Pat sees "HA HA HA - YOU LOSE!"
And the engine emits GameEnded with outcome="fell_in_pit"
```

#### Scenario: Pat is teleported by a bat into a safe room

```gherkin
Given a bat is in room 5 and the next bat-teleport draw will land Pat in room 17
And no hazard occupies room 17
When Pat moves to room 5
Then Pat sees "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!"
And Pat sees the sense lines for room 17
And Pat sees "YOU ARE IN ROOM 17"
And the game continues
```

#### Scenario: Pat is teleported by a bat into a pit

```gherkin
Given a bat is in room 5 and a pit is in room 17 and the next bat-teleport draw is room 17
When Pat moves to room 5
Then Pat sees "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!"
And Pat sees "YYYIIIIEEEE . . . FELL IN PIT"
And Pat sees "HA HA HA - YOU LOSE!"
```

#### Scenario: Pat bumps the wumpus and the wumpus startles to a safe room

```gherkin
Given the wumpus is in room 7 and Pat is in room 8 adjacent to room 7
And the engine's next startle roll will be 1 and that startle target is not Pat's room
When Pat moves to room 7
Then Pat sees "...OOPS! BUMPED A WUMPUS!"
And the wumpus has moved to S(7, 1)
And the game continues
```

#### Scenario: Pat bumps the wumpus and the wumpus startles onto Pat

```gherkin
Given the wumpus is in room 7 and Pat enters room 7
And the engine's startle roll will move the wumpus back onto Pat's room
When the startle resolves
Then Pat sees "TSK TSK TSK- WUMPUS GOT YOU!"
And Pat sees "HA HA HA - YOU LOSE!"
And the engine emits GameEnded with outcome="eaten_after_bump"
```

#### Scenario: No sense fires for non-adjacent hazards

```gherkin
Given the wumpus, pits, and bats are all placed in rooms not adjacent to room 12
When Pat enters room 12
Then Pat sees no "I SMELL A WUMPUS!" line
And Pat sees no "I FEEL A DRAFT" line
And Pat sees no "BATS NEARBY!" line
And Pat sees only "YOU ARE IN ROOM 12" and "TUNNELS LEAD TO ..."
```

### Acceptance Criteria

- [ ] AC-03.1 — Sense emission on room entry: one `SenseEmitted` event per adjacent hazard, in L-array order (wumpus → pit → pit → bat → bat).
- [ ] AC-03.2 — Walking into wumpus emits `BUMPED_WUMPUS` text + triggers startle (FNC ∈ {1,2,3}: move; FNC=4: stay); if startled wumpus lands on player, `TSK TSK TSK...` + `HA HA HA - YOU LOSE!`.
- [ ] AC-03.3 — Walking into pit emits `FELL_IN_PIT` text + `HA HA HA - YOU LOSE!` + `GameEnded(outcome=fell_in_pit)`.
- [ ] AC-03.4 — Walking into bat emits `BAT_SNATCH` text + teleports to uniformly random room (any of 20, including hazard rooms) + recursively re-enters the destination.
- [ ] AC-03.5 — Bat chain into pit terminates game with pit message and lose message.
- [ ] AC-03.6 — Sense events precede `LocationReported` events in the stream (event ordering, not just printing).
- [ ] AC-03.7 — `MESSAGES[LOSE]` is the exact Yob-source string `HA HA HA - YOU LOSE!` (C-1 fidelity).

### Outcome KPIs

- **Who:** Player Pat
- **Does what:** plays a hazard-populated game and dies or survives based on Yob-faithful rules
- **By how much:** 100% of senses match adjacency; 100% of hazard outcomes match Yob's branching (including bat-chain-into-pit); 100% of loss messages are byte-identical to Yob source
- **Measured by:** acceptance test suite running scripted scenarios; unit test asserting `MESSAGES[LOSE]` equals Yob line 0520
- **Baseline:** None

### Technical Notes

- Constraints: C-1, C-2, C-6.
- Dependencies: US-01, US-02 (skeleton CLI loop).
- Estimated effort: 3 days.
- Right-sized: 7 scenarios, 3 days, single demoable behavior class (passive ruleset).

### Story Size

3 days | 7 scenarios | demoable as: "I can lose a game by walking into a hazard, including a bat-into-pit chain."

---

## US-04: Shooting end-to-end — path, walk, hit/miss, startle, self-shot, out-of-arrows

### Elevator Pitch

- **Before:** Pat can play a hazard game but cannot win it — there is no shooting.
- **After:** Pat types `S`, is prompted `NO. OF ROOMS(1-5)?`, then `ROOM #?` repeatedly. The engine walks the arrow through her path, catching crooked-path attempts (Yob's "ARROWS AREN'T THAT CROOKED"), random-deflecting on missing tunnels, and resolving hit/miss/self-shot. On hit, `AHA! YOU GOT THE WUMPUS!` + `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!`. On miss, `MISSED` + the wumpus startles. On self-shot, `OUCH! ARROW GOT YOU!` + arrow count decrements. Run out of arrows: `HA HA HA - YOU LOSE!`.
- **Decision enabled:** Pat can complete a full Yob game from start to win or loss. Researchers can record full-game sessions for replay analysis.

### Job

`job_id: play-classic-wumpus`

### Problem

Pat cannot complete a recognizable game of Hunt the Wumpus without shooting. The shooting rules are also the most quirky and most often miscoded in reimplementations — crooked-arrow validation, random deflection, self-shot — so getting these right is the bulk of the fidelity work.

### Who

- **Player Pat** — 1973-game enthusiast
- **Context:** wants to play a complete game including the climactic arrow shot
- **Motivation:** the arrow rules are the part of Yob that most reimplementations get subtly wrong; this needs to be byte-faithful

### Solution

Implement the shoot subroutine per Yob lines 3000-3440: path collection with length validation (1-5), crooked-path validation (P(K) != P(K-2) when K > 2), arrow walk with adjacency check at each step, random deflection on missing tunnel (FNB ∈ {1,2,3}), hit-wumpus / hit-player / miss outcomes, wumpus startle on miss, arrow count decrement on miss or self-shot, out-of-arrows loss.

### Domain Examples

#### 1: Happy Path — Pat shoots and hits the wumpus through a 2-room path

Setup: Pat in room 8, wumpus in room 14. Adjacency: 8-7, 7-14.

```
SHOOT OR MOVE (S-M)? S
NO. OF ROOMS(1-5)? 2
ROOM #? 7
ROOM #? 14
AHA! YOU GOT THE WUMPUS!
HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!
SAME SET-UP (Y-N)?
```

#### 2: Edge — Pat enters a crooked path (room K-2 == room K)

```
SHOOT OR MOVE (S-M)? S
NO. OF ROOMS(1-5)? 3
ROOM #? 7
ROOM #? 14
ROOM #? 7
ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM
ROOM #? 15
```

#### 3: Edge — Pat's path begins with a non-adjacent room, arrow goes random

Setup: Pat in room 8 (adjacent to 1, 7, 9). She enters room 14 as the first path room (not adjacent). Engine's next FNB draw: 2 → first adjacency = room 7.

```
SHOOT OR MOVE (S-M)? S
NO. OF ROOMS(1-5)? 2
ROOM #? 14
ROOM #? 20
MISSED
```

(Arrow deflected to room 7 — Pat's second path entry ignored because deflection ends path-following. Then `MISSED`, wumpus startles, arrow decrements.)

#### 4: Error — Pat exhausts her last arrow

Setup: Pat has 1 arrow. Shoots, misses.

```
SHOOT OR MOVE (S-M)? S
NO. OF ROOMS(1-5)? 1
ROOM #? 7
MISSED
HA HA HA - YOU LOSE!
SAME SET-UP (Y-N)?
```

### UAT Scenarios (BDD)

#### Scenario: Pat shoots and wins with Yob's swapped message

```gherkin
Given Pat is in room 8 with 5 arrows
And the wumpus is in room 14
And rooms 8-7 and 7-14 are connected
When Pat shoots a 2-room path through rooms 7, 14
Then Pat sees "AHA! YOU GOT THE WUMPUS!"
And Pat sees "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!"
And the engine emits GameEnded with outcome="wumpus_shot" and message_kind="win"
```

#### Scenario: Pat misses, wumpus startles and stays put

```gherkin
Given Pat is in room 8 with 5 arrows
And the wumpus is in room 14 and Pat's path does not reach it
And the engine's next startle roll will be 4 (wumpus stays)
When Pat shoots
Then Pat sees "MISSED"
And the wumpus is still in room 14
And Pat has 4 arrows remaining
```

#### Scenario: Pat exhausts the last arrow and loses

```gherkin
Given Pat has 1 arrow and her shot will miss
When Pat shoots
Then Pat sees "MISSED"
And Pat sees "HA HA HA - YOU LOSE!"
And the engine emits GameEnded with outcome="out_of_arrows"
```

#### Scenario: Crooked path is rejected and re-prompts for that slot only

```gherkin
Given Pat is shooting and has entered rooms 7 and 14 for the first two path slots
When Pat enters 7 again for the third slot
Then Pat sees "ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM"
And the engine re-prompts "ROOM #?" for the third slot only
And the previously entered rooms 7 and 14 are unchanged
```

#### Scenario: Arrow takes a random tunnel when the path room is not adjacent

```gherkin
Given Pat is in room 8 (adjacent to 1, 7, 9)
And Pat's path begins with room 14 (not adjacent to 8)
When the arrow is walked
Then the arrow goes to a uniformly random adjacent room of room 8
And the remaining path rooms are not consulted
And the engine emits an ArrowPathStep event with deflected=True
```

#### Scenario: Arrow loops back through the dodecahedron and hits Pat

```gherkin
Given Pat is in room 8 with 5 arrows
And Pat enters a 4-room path that traverses back to room 8
When the arrow lands on room 8
Then Pat sees "OUCH! ARROW GOT YOU!"
And Pat has 4 arrows remaining (decremented as if a miss)
And the game continues
```

#### Scenario: Pat misses and the wumpus startles onto her

```gherkin
Given Pat is in room 8 and the wumpus is in room 1 adjacent to room 8
And Pat's shot misses
And the engine's next startle roll moves the wumpus from room 1 to room 8
When the startle resolves
Then Pat sees "MISSED"
And Pat sees "TSK TSK TSK- WUMPUS GOT YOU!"
And Pat sees "HA HA HA - YOU LOSE!"
```

### Acceptance Criteria

- [ ] AC-04.1 — Path length input must be 1-5 inclusive; out-of-range re-prompts (Yob line 3060).
- [ ] AC-04.2 — Crooked-path validation: when K > 2, P(K) != P(K-2); otherwise `ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM` and re-prompt for slot K only (not for the whole path).
- [ ] AC-04.3 — Arrow walk: at each step K, if S(L, K1) == P(K) for some K1 ∈ {1,2,3}, arrow advances to P(K); else arrow advances to S(L, FNB(1)) and stops consulting remaining path (Yob lines 3170-3210).
- [ ] AC-04.4 — Arrow hit wumpus: `AHA! YOU GOT THE WUMPUS!` + `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!` + `GameEnded(outcome=wumpus_shot)`.
- [ ] AC-04.5 — Arrow hit player (self-shot): `OUCH! ARROW GOT YOU!` + arrow count decrements + game continues (Yob 3340-3360 falls through to 3270).
- [ ] AC-04.6 — Arrow miss: `MISSED` + wumpus startle (FNC ∈ {1,2,3}: move via S(L(2),K); FNC=4: stay) + arrow count decrements.
- [ ] AC-04.7 — Wumpus startle onto player after miss: `TSK TSK TSK- WUMPUS GOT YOU!` + `HA HA HA - YOU LOSE!` + `GameEnded(outcome=eaten_after_miss)`.
- [ ] AC-04.8 — Out of arrows: `HA HA HA - YOU LOSE!` + `GameEnded(outcome=out_of_arrows)`.
- [ ] AC-04.9 — `MESSAGES[WIN]` is the exact Yob-source string `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!` (Decision 3 / C-1 fidelity).

### Outcome KPIs

- **Who:** Player Pat
- **Does what:** completes a full game ending in win, eaten, self-shot loss, or out-of-arrows loss
- **By how much:** 100% of arrow-rule scenarios match Yob's branching; 100% of win/lose messages preserve the famous swap
- **Measured by:** acceptance test suite covering all 7 arrow scenarios; unit test asserting `MESSAGES[WIN]` equals Yob line 0550
- **Baseline:** None

### Technical Notes

- Constraints: C-1, C-2, C-6.
- Dependencies: US-01, US-02, US-03 (wumpus must exist to be shot).
- Estimated effort: 3 days (most-edge-cases story; this is where the rule-fidelity work concentrates).
- Right-sized: 7 scenarios, 3 days. The single demoable behavior class (shooting) cannot be split smaller without breaking the "demoable in a session" criterion.

### Story Size

3 days | 7 scenarios | demoable as: "I can shoot the wumpus, miss and have it move, shoot myself, run out of arrows."

---

## US-05: Seeded replay produces byte-identical event streams

### Elevator Pitch

- **Before:** Harriet records an interesting LLM-game session and tries to reproduce it. She instantiates `Game()` and replays the command sequence — but the events differ from the original because she had no seed. The interesting case is now folklore.
- **After:** Harriet reads the seed from her recorded transcript header, instantiates `Game(seed=42)`, replays the recorded command sequence, and the event list is byte-identical to the original. The interesting case is reproducible.
- **Decision enabled:** Harriet can attach a debugger to a specific replayed turn; share a single seed value with collaborators for joint analysis; build automated regression tests from interesting sessions.

### Job

`job_id: replay-wumpus-deterministically`

### Problem

Harriet runs thousands of games unattended. When one produces an interesting LLM divergence event, she needs to replay just that game to investigate. She finds it painful to grep through a 10,000-line transcript log for the original RNG state — and impossible if there was no RNG state to begin with.

### Who

- **Harness Harriet** — researcher running experiment loops
- **Context:** post-hoc analysis of recorded sessions
- **Motivation:** zero tolerance for "I can't reproduce it"

### Solution

Engine's RNG is a single `random.Random(seed)` instance created at construction. Every game-state-affecting random draw goes through this instance, in a deterministic order. Replay is `Game(seed=recorded_seed)` + apply the recorded command sequence — guaranteed byte-identical events.

### Domain Examples

#### 1: Happy Path — Harriet replays a recorded session

```python
header = parse_transcript_header("session_2026_05_15.jsonl")
# header.seed == 42
recorded_events = load_events("session_2026_05_15.jsonl")
recorded_commands = [e for e in recorded_events if e.kind == "ActionChosen"]

g = Game(seed=42)
captured = []
g.events.subscribe(captured.append)
for cmd in recorded_commands:
    g.step(cmd.raw_input)

assert captured == recorded_events  # byte-identical
```

#### 2: Edge — Replay with a different seed diverges visibly

```python
g = Game(seed=43)  # different seed
captured = []
g.events.subscribe(captured.append)
for cmd in recorded_commands:
    g.step(cmd.raw_input)

assert captured[0].layout_hash != recorded_events[0].layout_hash
# Engine does NOT pretend they match — divergence is visible at GameStarted
```

#### 3: Edge — Attaching a sink does not change replay

```python
g1 = Game(seed=42); e1 = []; g1.events.subscribe(e1.append)
g2 = Game(seed=42); e2 = []; g2.events.subscribe(e2.append)
g2.events.subscribe(JsonlSink("/tmp/out.jsonl"))  # extra sink

for cmd in commands:
    g1.step(cmd); g2.step(cmd)

assert e1 == e2  # extra sink did not alter g2's events
```

### UAT Scenarios (BDD)

#### Scenario: Seeded replay is byte-identical

```gherkin
Given Harriet has recorded session X from Game(seed=42) with command sequence C
When Harriet creates Game(seed=42) and applies C
Then the new event sequence equals X's event sequence event-for-event
And every event payload field is bitwise equal
```

#### Scenario: Different seed diverges from replay

```gherkin
Given Harriet has recorded session X from Game(seed=42)
When Harriet creates Game(seed=43) and applies X's command sequence
Then the GameStarted layout_hash differs from X's
And the divergence is visible from the first event
And the engine does not silently coerce the layouts to match
```

#### Scenario: 20 seeded scenarios all replay byte-identical

```gherkin
Given Harriet has a fixture of 20 seeds, each with a recorded 50-turn command sequence
When Harriet replays each scenario
Then 20 of 20 replays produce byte-identical event sequences
```

#### Scenario: Replay determinism is independent of sink attachment

```gherkin
Given two Game instances with seed=42 and identical command sequences
And one instance has zero sinks attached, the other has a JsonlSink attached
When both run the command sequence
Then both instances emit identical event sequences
```

#### Scenario: Replay determinism is independent of subscription order

```gherkin
Given a Game instance with seed=42
And two sinks subscribed in order [A, B]
When the same scenario runs with sinks subscribed in order [B, A]
Then the event sequence is identical
And the order of dispatch to sinks is well-defined (subscription order)
```

### Acceptance Criteria

- [ ] AC-05.1 — Engine uses a single `random.Random(seed)` instance; no other entropy source.
- [ ] AC-05.2 — RNG call sites are in a deterministic order: cave gen (one batch), then per-turn calls in fixed order (bat teleport before wumpus startle if both fire in the same turn, etc.).
- [ ] AC-05.3 — `Game(seed=N)` replayed with command sequence C produces an event list bitwise equal to the original recording across 20 distinct seeds and 50-turn sequences.
- [ ] AC-05.4 — Different seed visibly diverges from replay (`layout_hash` differs).
- [ ] AC-05.5 — Replay is independent of sink count or attachment timing (C-3).

### Outcome KPIs

- **Who:** Harness Harriet
- **Does what:** reproduces any recorded session from its seed
- **By how much:** 20 of 20 seeded scenarios replay byte-identical
- **Measured by:** `tests/test_replay_determinism.py` running 20 seeds x 50 turns
- **Baseline:** None

### Technical Notes

- Constraints: C-2 (single RNG), C-3 (observer-effect absence), C-4 (event schema stable).
- Dependencies: US-01 (engine + seeded constructor); US-03, US-04 (full ruleset, since determinism is tested over the full game not just movement).
- Estimated effort: 2 days. (The work is mostly auditing existing code for non-RNG entropy and writing the determinism harness.)
- Right-sized: 5 scenarios, 2 days.

### Story Size

2 days | 5 scenarios | demoable as: "I can replay any recorded session from its seed and get byte-identical events."

---

## US-06: Concurrent CLI + JSONL sink — observer-effect absent

### Elevator Pitch

- **Before:** Harriet wants to monitor a live Pat session but has to choose: either Pat plays interactively (and Harriet only sees the stdout) or Harriet captures structured events (and Pat doesn't get the CLI). The user explicitly named this use case during scoping: "run experiments where I monitor events and telemetry while a user is playing a game."
- **After:** Pat runs `wumpus --transcript /tmp/session.jsonl`. Pat sees the same CLI she'd see without `--transcript`, byte-for-byte. Harriet (or her tooling) reads `/tmp/session.jsonl` concurrently and sees the complete event sequence in JSONL form. Neither view alters the other.
- **Decision enabled:** Harriet can instrument live human games for studies without affecting the human's experience. She can also tee the same session to multiple sinks (a file for the record + an in-memory queue for live analysis).

### Job

`job_id: instrument-wumpus-play`

### Problem

Harriet needs Decision 4's contract enforced: the engine's emission must be unaffected by the number or kind of attached sinks. She finds it painful to debug studies where she can't tell whether an interesting Pat behavior was caused by the game or by her observation of it.

### Who

- **Harness Harriet** — researcher instrumenting human-subject studies
- **Context:** wants live event capture from human gameplay sessions
- **Motivation:** observer-effect-free instrumentation; multi-sink fan-out

### Solution

Engine's `EventBus` dispatches each event to all subscribed sinks. Sinks are pure observers — they cannot influence engine state. Dispatch order is deterministic (subscription order). Exceptions from sinks are caught and logged without aborting the engine.

### Domain Examples

#### 1: Happy Path — Pat plays, transcript captures

```
$ wumpus --seed 42 --transcript /tmp/session.jsonl
INSTRUCTIONS (Y-N)? N
HUNT THE WUMPUS
I SMELL A WUMPUS!
YOU ARE IN ROOM  8
TUNNELS LEAD TO  1  7  9

SHOOT OR MOVE (S-M)? M
WHERE TO? 7
...

$ head -3 /tmp/session.jsonl
# wumpus_classic v0.1.0  seed=42  layout-hash=0xa3f1c2...
{"kind":"GameStarted","seed":42,"layout_hash":"a3f1c2","snapshot":{...}}
{"kind":"SenseEmitted","sense_kind":"WUMPUS_SMELL","from_room":8}
```

#### 2: Edge — Same seeded session, with and without `--transcript`, has identical stdout

```bash
$ wumpus --seed 42 < commands.txt > stdout_a.txt
$ wumpus --seed 42 --transcript /tmp/t.jsonl < commands.txt > stdout_b.txt
$ diff stdout_a.txt stdout_b.txt
# (no output — files are identical)
```

#### 3: Edge — A sink that raises does not kill Pat's session

Setup: Harriet attaches a buggy sink that raises `ValueError` on every event.

```python
game.events.subscribe(BrokenSink())  # raises on every dispatch
game.step("M 7")  # Pat's session continues; broken sink's exception is logged
```

### UAT Scenarios (BDD)

#### Scenario: CLI stdout is identical with or without --transcript

```gherkin
Given Pat runs "wumpus --seed 42 < commands.txt > stdout_a.txt"
And Pat runs "wumpus --seed 42 --transcript /tmp/t.jsonl < commands.txt > stdout_b.txt"
When the two stdout files are compared
Then they are byte-identical
```

#### Scenario: JSONL transcript captures the complete event sequence

```gherkin
Given Pat runs "wumpus --seed 42 --transcript /tmp/t.jsonl"
And Pat plays a session ending in GameEnded or SessionAborted
When the JSONL file is parsed
Then it contains every event the engine emitted, in order
And the first non-header line is GameStarted
And the last line is either GameEnded or SessionAborted
```

#### Scenario: Multiple sinks see identical event streams

```gherkin
Given Harriet attaches three sinks to a single Game instance: a JsonlSink, an in-memory list sink, and a queue sink
When a scenario runs
Then all three sinks receive the same events in the same order
```

#### Scenario: A sink that raises does not crash the engine

```gherkin
Given Harriet attaches a sink that raises ValueError on every dispatch
When the engine emits any event
Then the engine continues processing
And the exception is logged once per sink (not per event, to avoid spam)
And other sinks still receive the event
```

#### Scenario: Engine emits identical event streams with 0 vs N sinks

```gherkin
Given two Game instances with seed=42 and identical command sequences
And instance A has zero sinks attached
And instance B has 5 sinks attached
When both run the command sequence
Then both instances produce identical internal event histories
```

### Acceptance Criteria

- [ ] AC-06.1 — `--transcript PATH` writes a JSONL file with one header line + one event per line.
- [ ] AC-06.2 — Pat's stdout is byte-identical whether `--transcript` is passed or not (for the same seed and command sequence).
- [ ] AC-06.3 — Multiple sinks can be attached; each receives the full event sequence in subscription order.
- [ ] AC-06.4 — A sink that raises is isolated: its exception is logged once, other sinks still receive the event, engine continues.
- [ ] AC-06.5 — Engine event emission is identical with 0, 1, or N sinks attached (no observer effect — C-3).
- [ ] AC-06.6 — Transcript header line format: `# wumpus_classic v<version>  seed=<N>  layout-hash=<hex>`.

### Outcome KPIs

- **Who:** Harness Harriet
- **Does what:** monitors a live Pat session via JSONL tee without affecting Pat's experience
- **By how much:** 100% of dual-mode runs (with/without --transcript) produce byte-identical stdout
- **Measured by:** `tests/test_concurrent_sink.py` running matched pairs and diffing stdouts
- **Baseline:** None

### Technical Notes

- Constraints: C-3 (observer-effect absence is THE invariant for this story), C-4 (JSONL schema stability).
- Dependencies: US-01, US-02 (CLI exists), US-05 (determinism is required for the diff to be meaningful).
- Estimated effort: 2 days.
- Right-sized: 5 scenarios, 2 days.

### Story Size

2 days | 5 scenarios | demoable as: "I can tee a live human session to JSONL with no visible effect on the player."

---

## US-07: Oracle parity — engine output matches PC-BASIC byte-for-byte (modulo seed mapping)

### Elevator Pitch

- **Before:** The fidelity claim ("byte-recognizable Yob 1973") is a self-assessment. The audit trail exists (`g_wild_baseline/`) but isn't continuously checked against the engine.
- **After:** A CI test takes 10 hand-curated scenarios. For each, it runs `pcbasic wumpus.gwbasic.bas` via `wexpect`, captures stdout, and compares to the engine's CLI output for the layout-matched seed. Byte-equality means the engine emits Yob-faithful text for those scenarios. Failure means a rule has drifted.
- **Decision enabled:** Researchers can cite "passes oracle-parity on N scenarios" as evidence for the fidelity claim. Regressions are caught before release.

### Job

`job_id: play-classic-wumpus`

(This story produces the evidence for KPI 4 and underwrites the fidelity claims of US-01 through US-04.)

### Problem

Pat and Harriet both rely on the fidelity claim, but neither can independently verify it without running PC-BASIC themselves and eyeballing diffs. The engineering team needs an automated regression guard against fidelity drift introduced by future changes.

### Who

- **Engineering team** (acting on behalf of Pat and Harriet)
- **Context:** continuous integration on Windows runner (wexpect is Windows-only per `g_wild_baseline/README.md`)
- **Motivation:** automated guard against silent fidelity regressions

### Solution

A test harness `tests/oracle_parity/` containing:
1. 10 fixture scenarios, each defining: a starting layout (player room, wumpus, pits, bats) + a command sequence
2. A `pcbasic` runner via `wexpect` that injects the layout (by pre-seeding a layout-disclosure patch into the BASIC source for that test run only) and runs the command sequence
3. An engine runner that constructs `Game(seed=<seed-known-to-produce-this-layout>)` and runs the same command sequence with the CLI renderer
4. A byte-comparator that diffs the two stdouts

### Domain Examples

#### 1: Happy Path — Scenario "shoot-and-win" passes

```
Fixture: tests/oracle_parity/fixtures/shoot_and_win.yaml
  layout: { player: 8, wumpus: 14, pits: [2, 11], bats: [5, 18] }
  commands: ["N", "S", "2", "7", "14"]

Expected engine stdout = PC-BASIC stdout (byte-identical)
```

#### 2: Edge — Scenario "bat-into-pit-chain" passes

```
Fixture: bat_into_pit_chain.yaml
  layout: { player: 4, wumpus: 1, pits: [17], bats: [5, 9], pits2: [12] }
  commands: ["N", "M", "5"]
  forced_rng_event: bat teleport target = 17  # via test seed selection

Both engine and PC-BASIC must emit:
  ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!
  YYYIIIIEEEE . . . FELL IN PIT
  HA HA HA - YOU LOSE!
```

#### 3: Error — A regression breaks the test

```
Fixture: senses_in_yob_order.yaml
  Engine output: "I FEEL A DRAFT\nI SMELL A WUMPUS!\n..."  (wrong order — refactor bug)
  PC-BASIC output: "I SMELL A WUMPUS!\nI FEEL A DRAFT\n..."
  Diff fails -> CI fails -> regression caught
```

### UAT Scenarios (BDD)

#### Scenario: All 10 oracle-parity fixtures pass

```gherkin
Given a CI runner with pcbasic and wexpect installed
And the test fixture set with 10 hand-curated scenarios
When the oracle parity test suite runs
Then all 10 fixtures produce byte-identical stdout between engine and PC-BASIC
```

#### Scenario: A fidelity regression is caught by the suite

```gherkin
Given the engine has a bug that prints senses in the wrong order
When the oracle parity test suite runs
Then at least one fixture fails with a unified diff showing the offending line
And the CI build fails
```

#### Scenario: Rule coverage gate passes

```gherkin
Given the audited rule list in shared-artifacts-registry.md
And the acceptance test scenarios across US-01 through US-04
When the rule-coverage gate runs
Then every audited rule is referenced by at least one scenario
And no rule is missing coverage
```

### Acceptance Criteria

- [ ] AC-07.1 — Test fixture set contains at least 10 scenarios covering: shoot-win, miss-startle, bat-into-pit, wumpus-bump-startle-eats-player, self-shot, out-of-arrows, multi-sense room, no-sense room, same-setup replay, instructions-on.
- [ ] AC-07.2 — Each fixture runs both engine and `pcbasic wumpus.gwbasic.bas` via `wexpect`, captures stdouts, asserts byte-equality.
- [ ] AC-07.3 — Layout-matching strategy is documented (test-only BASIC source patch that pins the layout, or seed-search that finds an engine seed whose generated layout matches the fixture's required layout).
- [ ] AC-07.4 — Rule-coverage gate: every rule in `shared-artifacts-registry.md` constants tables has at least one scenario referencing it (via `@yob-LINE` tag or rule name in scenario description).
- [ ] AC-07.5 — Test runs on Windows CI runner only (wexpect platform constraint); on non-Windows CI, the test suite is skipped with a clear message, not silently passed.

### Outcome KPIs

- **Who:** Engineering team (on behalf of Pat and Harriet)
- **Does what:** validates the fidelity claim against the BASIC reference on every commit
- **By how much:** 10/10 fixtures pass; 100% rule-coverage gate green
- **Measured by:** `tests/oracle_parity/` suite + `tests/test_rule_coverage.py`
- **Baseline:** None

### Technical Notes

- Constraints: C-1 (this story IS the fidelity verifier).
- Dependencies: US-01 through US-04 (all rules implemented); the `wumpus/experiments/g_wild_baseline/` directory (already exists).
- Estimated effort: 3 days (fixture curation + wexpect/pcbasic harness + seed/layout matching).
- Right-sized: 3 scenarios at the story level; the fixture set itself has 10 scenarios but those are *data*, not separate UATs.

### Story Size

3 days | 3 scenarios + 10 fixtures | demoable as: "CI runs PC-BASIC and the engine side-by-side and they produce identical stdout."

---

## Story summary

| ID | Title | Slice | Days | Scenarios | Job |
|---|---|---|---|---|---|
| US-01 | Engine boots with seeded cave and emits structured events | 1 (skeleton) | 2 | 5 | instrument-wumpus-play |
| US-02 | CLI loop runs end-to-end with movement-only gameplay | 1 (skeleton) | 2 | 6 | play-classic-wumpus |
| US-03 | Hazards, senses, walking-into-hazards | 2 | 3 | 7 | play-classic-wumpus |
| US-04 | Shooting end-to-end | 3 | 3 | 7 | play-classic-wumpus |
| US-05 | Seeded replay produces byte-identical event streams | 4 | 2 | 5 | replay-wumpus-deterministically |
| US-06 | Concurrent CLI + JSONL sink — observer-effect absent | 4 | 2 | 5 | instrument-wumpus-play |
| US-07 | Oracle parity — engine matches PC-BASIC byte-for-byte | 5 | 3 | 3 + 10 fixtures | play-classic-wumpus |

**Total:** 7 stories, 17 days of effort, 38 acceptance scenarios + 10 fixtures.

All stories validation status: `synthesized-from-informal-notes` (per wave-decisions.md: no DISCOVER or DIVERGE artifacts upstream).
