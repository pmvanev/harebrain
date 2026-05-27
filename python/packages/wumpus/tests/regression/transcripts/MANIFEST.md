# Golden rendered-transcript fixtures (R1-S13)

The structural successor to the withdrawn R1-S10 BASIC fixtures (see ADR-011 in
`docs/feature/wumpus/feature-delta.md`). Each `.txt` here is the engine's OWN
full rendered stdout for a fixed `(seed, input-script)` CLI session that runs to
a distinct terminal. The characterization test
(`tests/regression/test_rendered_transcript_golden.py`) re-drives
`wumpus.cli.main` in-process with `io.StringIO` and asserts the captured stdout
equals the pinned `.txt` byte-for-byte (newline-normalized to `\n`).

This is **engine-vs-pinned-self**, NOT engine-vs-BASIC. The transcripts pin the
engine's faithful Yob rendering against itself; any rendering regression
surfaces as a diff. **Re-bless deliberately** on an intended rendering change by
regenerating the `.txt` files (see the test module's `bless` note).

The `input-script` is the Yob two-step CLI input form — what a player types:
single-letter `N`/`S`/`M`/`Y` and bare integers, one per line, ending with
`SAME SET-UP (Y-N)?` → `N` to exit cleanly.

| Fixture | seed | argv | input-script | Terminal kind |
|---|---|---|---|---|
| `pit_fall_seed3.txt` | 3 | `--seed 3` | `N` `M` `19` `N` | Pit-fall loss (`YYYIIIIEEEE . . . FELL IN PIT` + `HA HA HA - YOU LOSE!`) |
| `wumpus_kill_seed15.txt` | 15 | `--seed 15` | `N` `S` `1` `7` `N` | Wumpus-kill win (`AHA! YOU GOT THE WUMPUS!` + `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!`) |
| `bump_eaten_seed18.txt` | 18 | `--seed 18` | `N` `M` `6` `N` | Wumpus-bump-eaten loss (`...OOPS! BUMPED A WUMPUS!` + `TSK TSK TSK- WUMPUS GOT YOU!` + `HA HA HA - YOU LOSE!`) |

## Seed discovery notes

- **seed=3** is the engine-verified forced pit-fall already pinned by
  `tests/regression/test_determinism_golden_master.py` (player starts in room
  20, neighbors {13, 16, 19}; room 19 holds a pit). Walking `M`/`19` falls in.
- **seed=15** places the player in room 8 (neighbors {1, 7, 9}) with the wumpus
  in adjacent room 7. A 1-room shoot (`S`/`1`/`7`) walks the arrow straight into
  the wumpus's room — a clean kill before any startle can move it off-target.
- **seed=18** places the player in room 7 (neighbors {6, 8, 17}) with the wumpus
  in adjacent room 6. Bumping into room 6 (`M`/`6`) startles the wumpus onto the
  player's room for this seed → eaten-after-bump loss. This session also
  exercises the `BATS NEARBY!` sense line (seed=18 has a bat adjacent to room 7),
  broadening verbatim-string coverage beyond the other two transcripts.

## Observed rendering characteristic (not a bug to fix here)

The pit-fall transcript renders `YYYIIIIEEEE . . . FELL IN PIT` **twice** — once
on `HazardTriggered(PIT)` and once on `GameEnded(fell_in_pit)`. That is the
engine's existing per-event rendering behavior (each event independently maps to
its surface line). R1-S13 is a test-only slice: it pins the engine's OWN output
as-is. If the double-render is ever judged undesirable, that is a separate
render-layer change with its own slice — re-bless these fixtures then.
