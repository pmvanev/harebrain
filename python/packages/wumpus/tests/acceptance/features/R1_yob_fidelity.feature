# R1 Yob fidelity — acceptance criteria
#
# Each R1 slice appends its scenarios to this file. R1-S01 ships the first 4
# scenarios (dodecahedron + cave gen from seed); subsequent R1 slices append
# their own scenarios as they land.
#
# Pre-conditions all R1 scenarios share:
#   - The real 20-room dodecahedron (NOT the R0 toy cave)
#   - Yob's FNB rejection-loop entity placement
#   - Seeded RNG via the engine's internal random.Random instance
#   - Placeholder surface strings (real Yob surface lands at R4-S03)

Feature: R1 Yob fidelity — dodecahedron cave + Yob mechanics

  As a researcher driving harness experiments
  I want Game(seed=k) to produce a deterministic dodecahedron layout
  with the audited 20x3 adjacency and Yob's FNB entity placement
  So that seeded replays and cross-cell comparisons share a known geometry
  without any per-run regeneration drift.

  # ---------------------------------------------------------------------------
  # R1-S01 — Dodecahedron + cave gen from seed
  # ---------------------------------------------------------------------------

  Scenario: Layout is determined by seed
    Given seed = 42
    When Game(seed=42) is constructed twice in separate Python processes
    Then both constructions produce identical _initial_layout (wumpus room, pit rooms, bat rooms, player start)

  Scenario: All entity rooms are distinct
    Given Game(seed=k) for any integer k
    Then the wumpus room, both pit rooms, both bat rooms, and the player start are all distinct rooms

  Scenario: Adjacency is the audited 20x3 dodecahedron
    Given the wumpus.constants.DODECAHEDRON table
    Then it matches the 20x3 table in the archived shared-artifacts-registry (rooms 1-20 with their three tunnels each)

  Scenario: random.Random stability regression
    Given a Python 3.11+ interpreter
    When random.Random(42).randrange(20) is invoked
    Then the result equals a pinned constant (catches Python-stdlib drift at CI time)

  # ---------------------------------------------------------------------------
  # R1-S02 — Sense emit on entry (Yob L-array order)
  # ---------------------------------------------------------------------------

  Scenario: Senses fire in L-array order
    Given the player enters a room adjacent to the wumpus AND adjacent to a pit
    Then a SenseEmitted(WUMPUS_SMELL) event fires
    And then a SenseEmitted(PIT_DRAFT) event fires
    And then a LocationReported event fires

  Scenario: Repeated same-kind hazards repeat the sense
    Given the player enters a room adjacent to two pits
    Then two SenseEmitted(PIT_DRAFT) events fire (one per adjacency match)

  Scenario: No sense fires for a non-adjacent hazard
    Given the player enters a room with no adjacent hazards
    Then no SenseEmitted event fires before LocationReported

  # ---------------------------------------------------------------------------
  # R1-S03 — Move + wumpus bump + startle
  # ---------------------------------------------------------------------------

  Scenario: Bumping the wumpus triggers startle to an adjacent room
    Given the wumpus is in room 7 and the player is in room 8 (adjacent to 7)
    And the engine's next startle draw will be 1 (move to first adjacent room)
    When the player moves to room 7
    Then a HazardTriggered(WUMPUS) event fires
    And a WumpusStartled(from=7, to=<first-adjacent-of-7>, ate_player=False) event fires
    And the game continues

  Scenario: Bumping the wumpus and being eaten
    Given the wumpus is in room 7 and the player is in room 8
    And the engine's next startle draw will leave the wumpus on room 8 (the player's room)
    When the player moves to room 7
    Then a HazardTriggered(WUMPUS) event fires
    And a WumpusStartled(ate_player=True) event fires
    And a GameEnded(outcome=eaten_after_bump) event fires

  Scenario: 25% stay-put rule
    Given the wumpus is in room 7 and the player is in room 8
    And the engine's next startle draw will be 4 (stay)
    When the player moves to room 7
    Then WumpusStartled(from=7, to=7, ate_player=True) fires (the wumpus stays in 7, which is now the player's room)

  # ---------------------------------------------------------------------------
  # R1-S04 — Move + pit + bat teleport (recursive)
  # ---------------------------------------------------------------------------

  Scenario: Falling into a pit ends the game
    Given a pit is in room 4 and the player is in room 3 (adjacent to 4)
    When the player moves to room 4
    Then HazardTriggered(PIT) fires
    And GameEnded(outcome=fell_in_pit) fires

  Scenario: Bat teleport to a safe room re-emits senses for the new room
    Given a bat is in room 5 and the engine's next bat-teleport target is room 17
    And room 17 is adjacent to no hazards
    When the player moves to room 5
    Then PlayerTeleported(from=5, to=17) fires
    And LocationReported(room=17) fires
    And no SenseEmitted event fires for the new room

  Scenario: Bat teleport into a pit ends the game (recursive hazard)
    Given a bat is in room 5 and a pit is in room 17
    And the engine's next bat-teleport target is room 17
    When the player moves to room 5
    Then PlayerTeleported(from=5, to=17) fires
    And HazardTriggered(PIT) fires
    And GameEnded(outcome=fell_in_pit) fires

  # ---------------------------------------------------------------------------
  # R1-S05 — Shoot path collection + crooked-arrow rejection
  # ---------------------------------------------------------------------------

  Scenario: Path-length out of range re-prompts
    Given the player has chosen S
    When the player enters 0 for NO. OF ROOMS(1-5)?
    Then NO. OF ROOMS(1-5)? is re-prompted
    And no turn counter advance has occurred

  Scenario: Crooked path triggers slot-specific re-prompt
    Given the player has entered path entries [7, 14] for a 3-room shoot
    When the player enters 7 for the third slot
    Then a CrookedPathRejected(slot=3, attempted_room=7) event fires
    And ROOM #? is re-prompted ONLY for slot 3
    And the previously-entered rooms 7 and 14 remain unchanged

  Scenario: Mid-shoot snapshot round-trips
    Given the player is mid-shoot, has entered NO. OF ROOMS=3 and ROOM #=7 for slot 1
    When game.snapshot() is taken and Game.from_snapshot(snap) is constructed
    Then the resurrected game prompts for ROOM #? at slot 2
    And the pending_arrow_path is [7]

  # ---------------------------------------------------------------------------
  # R1-S06 — Arrow walk + hit/miss/self-shot + out-of-arrows
  # ---------------------------------------------------------------------------

  Scenario: Successful shot kills the wumpus
    Given the player is in room 8 with 5 arrows
    And the wumpus is in room 17 and rooms 8-7, 7-17 are connected
    When the player shoots a 2-room path through rooms 7, 17
    Then ArrowFired(path=[7, 17]) fires
    And ArrowPathStep(room=7, deflected=False) fires
    And ArrowPathStep(room=17, deflected=False) fires
    And ArrowHitWumpus(room=17) fires
    And GameEnded(outcome=wumpus_shot) fires

  Scenario: Crooked arrow passing through player's room mid-path does NOT kill
    Given the player is in room 8 with 5 arrows
    And the arrow path walks rooms 7, then 8 (mid-path, passing through player), then 9
    When the arrow walks the path
    Then ArrowPathStep(room=8, deflected=False) fires (no ArrowHitPlayer)
    And ArrowPathStep(room=9, ...) fires
    And the player is unharmed at this step

  Scenario: Arrow's FINAL room matches player triggers self-shot
    Given the player is in room 8 and the arrow's final room is room 8
    Then ArrowHitPlayer(room=8) fires
    And ArrowCountChanged(new_count=4) fires (decrement-as-if-missed)
    And the game continues unless arrow count is now 0

  Scenario: Arrow takes random tunnel on missing connection
    Given the player is in room 8 and shoots a path beginning with room 14 (not adjacent to 8)
    When the arrow is walked
    Then ArrowPathStep(room=<random-adjacent-of-8>, deflected=True) fires
    And no further path rooms are consulted (remaining slots discarded)

  Scenario: Missing the wumpus startles it and decrements the arrow
    Given the player misses and the next startle draw will leave the wumpus in place
    Then ArrowMissed fires
    And WumpusStartled(moved=False) fires
    And ArrowCountChanged(new_count=<prev-1>) fires

  Scenario: Out of arrows ends the game
    Given the player has 1 arrow remaining and misses
    Then ArrowMissed fires
    And ArrowCountChanged(new_count=0) fires
    And GameEnded(outcome=out_of_arrows) fires

  # ---------------------------------------------------------------------------
  # R1-S07 — Terminal state + Yob win/lose message swap + SAME SET-UP
  # ---------------------------------------------------------------------------

  Scenario: Win message is Yob's swapped HEE HEE HEE text
    Given the player has just shot the wumpus
    Then GameEnded(outcome=wumpus_shot, message_kind=win) fires
    And the rendered_lines for the win turn contain "AHA! YOU GOT THE WUMPUS!"
    And the rendered_lines for the win turn contain "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!"

  Scenario: Loss message is Yob's swapped HA HA HA text
    Given the player has just fallen in a pit
    Then GameEnded(outcome=fell_in_pit, message_kind=lose) fires
    And the rendered_lines for the loss turn contain "YYYIIIIEEEE . . . FELL IN PIT"
    And the rendered_lines for the loss turn contain "HA HA HA - YOU LOSE!"

  Scenario: SAME SET-UP=Y restores the initial layout exactly
    Given the player has just finished a game with wumpus in 14, pits in 4 and 17, bats in 5 and 9, start 8
    When the player answers Y to SAME SET-UP (Y-N)?
    Then a new GameStarted event fires
    And the new game's _initial_layout equals the just-finished game's _initial_layout
    And the new game's layout_hash equals the just-finished game's layout_hash

  # ---------------------------------------------------------------------------
  # R1-S08 — Instructions block + RAMDOM typo preservation
  # ---------------------------------------------------------------------------

  Scenario: Instructions block contains Yob's RAMDOM typo
    Given the user answers Y to "INSTRUCTIONS (Y-N)?"
    Then the printed output contains the exact substring "RAMDOM" exactly once
    And the printed output ends with the "HUNT THE WUMPUS" banner before any game text begins

  Scenario: Answering N skips the instructions
    Given the user answers N to "INSTRUCTIONS (Y-N)?"
    Then the next printed output contains the "HUNT THE WUMPUS" banner
    And the captured output does NOT contain "RAMDOM"

  # ---------------------------------------------------------------------------
  # R1-S09 — CLI subprocess-safe (in-process line-buffering check)
  # ---------------------------------------------------------------------------
  #
  # The pexpect/wexpect subprocess smoke tests at `tests/subprocess/` exercise
  # the END-TO-END contract; this scenario is the SMOKE-TEST-INSURANCE that
  # the CLI loop flushes its prompts before reading input. The check runs
  # in-process (no subprocess overhead) by capturing the CLI's stdout into
  # a StringIO and asserting the INSTRUCTIONS prompt is present BEFORE the
  # CLI consumes any stdin.

  Scenario: Prompt is observable before input is awaited (in-process line-buffering check)
    Given a CLI invocation with seed 0 and a captured stdout stream
    When the CLI loop runs with a stdin that answers "N" to the instructions prompt
    Then the captured stdout contains "INSTRUCTIONS (Y-N)?" as a complete newline-terminated line
    And the prompt line appears before any further game text
