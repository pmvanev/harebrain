# Journey: Play Classic Wumpus (Visual)

Two personas share one engine. The CLI session that Pat sees and the event stream that Harriet consumes are two renderings of the same `Game.step()` calls.

## Persona overview

| Field | Player Pat | Harness Harriet |
|---|---|---|
| Surface | `wumpus` CLI binary | `from wumpus_classic import Game` |
| Input | line-buffered stdin (`S`/`M`, room numbers) | `game.step(command_str)` |
| Output | all-caps prompts, sense lines, terminal text | `(Snapshot, list[Event])` |
| Start feel | Curious / off-balance | Skeptical (does it match Yob?) |
| Middle feel | Tension (smell + draft + bats triangulation) | Trust (replays come back identical, events cover audited rules) |
| End feel | Catharsis (win or lose, message text is final) | Conviction (engine is the oracle) |
| Concurrency | Pat plays a session | Harriet's `EventSink` tees that same session to JSONL |

## Pat's journey — happy path with bat teleport

```
[trigger: `wumpus` typed]
        |
        v
+----- INSTRUCTIONS -----+        Feel: curious
| INSTRUCTIONS (Y-N)? N  |        Decision: skip (replayer) or read (new player)
+------------------------+
        |
        v
+------ ORIENT ---------+         Feel: orienting
| HUNT THE WUMPUS       |
| I SMELL A WUMPUS!     |         <- sense lines printed in Yob's order:
| I FEEL A DRAFT        |            wumpus, pit, pit, bat, bat (one per adjacency match)
| YOU ARE IN ROOM  8    |
| TUNNELS LEAD TO 1 7 9 |
+-----------------------+
        |
        v
+------ CHOOSE ---------+         Feel: weighing
| SHOOT OR MOVE (S-M)? M|
| WHERE TO? 7           |
+-----------------------+
        |
        v
+------ RESOLVE --------+         Feel: spike of dread (the "*ZAP*" is the first
| ZAP--SUPER BAT SNATCH!|          mental-map invalidation; Yob's bat is brutal)
| ELSEWHEREVILLE FOR YOU|
| BATS NEARBY!          |         <- sense lines for the *new* room print immediately
| YOU ARE IN ROOM 17    |          (Yob: bats land you, then re-enter location/hazard print loop)
| TUNNELS LEAD TO 7 16 18|
+-----------------------+
        |
        v
        ... (continues, eventually) ...
        |
        v
+------ TERMINAL -------+         Feel: catharsis
| AHA! YOU GOT THE      |
|   WUMPUS!             |
| HEE HEE HEE - THE     |         <- Yob's swap: WIN prints WUMPUS'LL GETCHA, LOSS prints HA HA HA
|   WUMPUS'LL GETCHA    |
|   NEXT TIME!!         |
| SAME SET-UP (Y-N)? N  |
+-----------------------+
```

Notes on the emotional arc — grounded in Yob's mechanics, not generic UX language:

- **Off-balance is the design.** The bat teleport (line 4270-4300 of the BASIC) drops the player in a uniformly random room and immediately reprints the location and sense lines for the new room. Every "I am in room 8" the player has built up in their head is invalidated in one turn. Confidence is *not* the goal for Pat — recognition is. A returning player feels "yes, the bat still ruins your day."
- **The smell is sticky.** The wumpus moves only on a missed arrow shot, with `P=0.75` to move one room and `P=0.25` to stay (line 3370-3440). So a smell three turns ago might still mean the wumpus is one room away — or not, if Pat fired and missed. The tension is *epistemic*, not visual.
- **The shot is one decision under uncertainty.** Crooked-arrow paths (1-5 rooms) are sequences of `WHERE TO?` prompts after a `NO. OF ROOMS(1-5)?` prompt. The arrow can hit the wumpus, miss and startle, or loop back and kill Pat. That last case (line 3340-3360, `OUCH! ARROW GOT YOU!`) is the cruelest payoff in the game.

## Harriet's journey — programmatic instrumentation

```
[trigger: `Game(seed=42)`]
        |
        v
+------ INSTANTIATE -----------+   Feel: skeptical
| game = Game(seed=42)         |   Q: is this reproducible? does it match Yob?
| snap = game.snapshot()       |
| # snap.layout - hazards,     |
| #   wumpus, player placed    |
| #   from FNA(seed) -> seq    |
+------------------------------+
        |
        v
+------ ATTACH SINK -----------+   Feel: setting up
| game.events.subscribe(       |
|   JsonlSink("session.jsonl") |
| )                            |
| game.events.subscribe(       |
|   queue_sink                 |
| )                            |
+------------------------------+
        |
        v
+------ STEP LOOP -------------+   Feel: trusting
| snap, evts = game.step("M 7")|   <- evts contains:
| #  [SenseEmitted(wumpus),    |       MoveAttempted, MoveResolved,
| #   MoveAttempted(from=8,    |       HazardTriggered (bat),
| #     to=7),                 |       PlayerTeleported (random new room),
| #   MoveResolved(to=7),      |       SenseEmitted (for new room)
| #   HazardTriggered(bat,17), |
| #   PlayerTeleported(to=17), |
| #   SenseEmitted(bat)]       |
+------------------------------+
        |
        v
+------ REPLAY VERIFY ---------+   Feel: conviction
| g2 = Game(seed=42)           |
| for cmd in recorded:         |
|   g2.step(cmd)               |
| assert g2.event_log ==       |
|   loaded_event_log           |   <- byte-identical events
+------------------------------+
        |
        v
+------ ORACLE USE ------------+   Feel: conviction
| for llm_turn in claimed:     |
|   oracle_state = replay(seed,|
|     moves[:turn])            |
|   if llm_claim != oracle:    |
|     log_divergence(turn,     |
|       field, claim, actual)  |
+------------------------------+
```

Notes on Harriet's arc:

- **Skepticism resolves through evidence, not assertion.** "Trust me, this matches Yob" doesn't satisfy her. The acceptance scenarios that prove rule coverage (every Yob rule has an event signature and a test) and seeded byte-identical replay are what move her from skeptical to trusting.
- **Conviction depends on observer-effect absence.** If hooking up a JSONL sink changes which rooms get generated, or which side the wumpus startles to, the engine fails its job. AC must lock this down.

## Concurrent rendering — Pat and Harriet on the same session

```
+----------------------+                     +-----------------------+
|  Pat at terminal     |                     |  Harness process      |
|  $ wumpus            |                     |  $ wumpus --json-tee  |
|                      |                     |    session.jsonl &    |
|                      |                     |    wumpus             |
|  reads stdin         |                     |  reads session.jsonl  |
|  sees rendered text  |                     |  reads structured     |
|                      |                     |    events             |
+----------+-----------+                     +-----------+-----------+
           |                                             |
           |                                             |
           |   +-------------------------------------+   |
           +---> wumpus_classic.Game                 <---+
               |                                     |
               |   step() emits Events to sinks:     |
               |     - CliRenderer (Pat's stdout)    |
               |     - JsonlSink (Harriet's file)    |
               |                                     |
               |   single source of truth: Game      |
               +-------------------------------------+

Mandatory invariant: Pat's stdout is byte-identical whether the JsonlSink is
attached or not. Harriet's JSONL contains the complete event sequence whether
the CliRenderer is attached or not.
```

This is Decision 4 made concrete. The harness use case ("monitor events and telemetry while a user is playing") drives the engine-with-sinks architecture.

## Shared artifacts at a glance

The full registry lives in `shared-artifacts-registry.md`. Headline items:

| Artifact | Source | Consumed by |
|---|---|---|
| Dodecahedron adjacency table | `wumpus_classic.constants.DODECAHEDRON` | engine cave gen, sense check, arrow path, move validation |
| Sense order on entry | `wumpus_classic.constants.SENSE_ORDER` (wumpus, pit, pit, bat, bat — Yob's L array order) | sense emitter, CLI renderer, event schema |
| Prompt strings | `wumpus_classic.constants.PROMPTS` | CLI renderer only |
| Outcome messages | `wumpus_classic.constants.MESSAGES` | CLI renderer only |
| Event schema | `wumpus_classic.events` | engine emit, JSONL sink, CLI renderer, harness consumers |
| Seed | constructor arg, printed in transcript header | engine, transcript, harness replay |

## Failure modes (input to DISTILL for negative-path scenarios)

| Step | Failure mode |
|---|---|
| Choose action | Pat types `X` (neither `S` nor `M`) — must re-prompt, no state change |
| Move resolve | Pat types `M 99` — must reject with `NOT POSSIBLE -` and re-prompt for `WHERE TO?` |
| Arrow path | Pat enters `0` or `6` for number of rooms — must re-prompt |
| Arrow path | Pat tries 1-2-1 path (room K-2 == room K) — `ARROWS AREN'T THAT CROOKED` and re-prompt for that room only |
| Arrow path | Pat's path enters an invalid tunnel mid-flight — arrow goes random (Yob's `S(L, FNB(1))`) |
| Replay | Harriet replays with a different seed — events diverge; engine must not silently pretend they match |
| Sink | A subscribed sink raises — engine must not crash Pat's session |
| Ctrl-C | Pat hits Ctrl-C mid-prompt — engine emits a `SessionAborted` event and exits cleanly |
