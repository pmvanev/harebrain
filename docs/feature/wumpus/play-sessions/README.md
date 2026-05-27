# Wumpus play-sessions

Recorded games against the `wumpus` engine — kept as demo artifacts and as
human-readable evidence that the DELIVER stack works end-to-end (deterministic
engine + Yob-faithful rendering + the two-step CLI + the JSONL ledger).

Each session is captured in two forms:

| File | Form | Audience |
|---|---|---|
| `*.txt` | the **stdout transcript** — exactly what a player sees | humans |
| `*.jsonl` | the **structured event ledger** (`--ledger`) — one schema-validated event per line | the LLM-vs-engine harness / analysis |

Both are byte-reproducible from the recorded `(seed, input-script)` because the
engine is deterministic (ADR-011: Python `random.Random` is the sole entropy
source).

---

## `seed1973-win.txt` / `seed1973-win.jsonl` — Claude wins by deduction

- **Seed:** 1973 (Yob's year) · **Outcome:** WIN (wumpus shot) · **Player:** Claude, playing fair (CLI output only — no peeking at the hidden layout)
- **Input script** (Yob two-step form): `N` · `M 16` · `M 17` · `M 16` · `M 20` · `M 13` · `S` `4` `20 16 15 6` · `N`

### Reproduce

From `python/packages/wumpus/`:

```bash
printf 'N\nM\n16\nM\n17\nM\n16\nM\n20\nM\n13\nS\n4\n20\n16\n15\n6\nN\n' \
  | uv run python -m wumpus --seed 1973 --ledger session.jsonl
```

(stdout is the `.txt`; `--ledger` writes the `.jsonl`.) Re-running produces
byte-identical output.

### Play-by-play (the reasoning behind each input)

The transcript shows only the engine's output (Yob never echoes input), so here
is what was typed and why:

| Turn | Observed | Deduction | Action |
|---|---|---|---|
| 1 | Room 15, **I SMELL A WUMPUS!**, tunnels 6/14/16 | Wumpus ∈ {6,14,16}; no pit/bat adjacent; every exit leads at a candidate so no safe retreat | `M 16` (2/3 safe; surviving eliminates 16) |
| 2 | Room 16 clean | 16 safe → wumpus ∈ **{6,14}** | `M 17` |
| 3 | Room 17, **BATS NEARBY!**, tunnels 7/16/18 | A bat is in 7 or 18 → scouting via room 7 is now too risky; reroute | `M 16` |
| 4–5 | Room 20 clean, tunnels 13/16/19 | 20 safe; 20→13 path is safe and 13 borders 14 (not 6) | `M 20`, `M 13` |
| 6 | Room 13, **no smell**, **BATS NEARBY!** | 13 borders 14 → *no* smell rules out 14 ⇒ wumpus is in **room 6** (second bat near 13; Yob has two) | (aim) |
| 7 | — | Verified tunnels 13→20→16→15→6 all connect and the path isn't crooked | `S 4` → `20 16 15 6` ⇒ **AHA! YOU GOT THE WUMPUS!** |

### Reading the ledger

The 53-event `.jsonl` is the same game as a typed event stream. Skeleton:

```
GameStarted → PromptIssued(instructions) → InstructionsShown
SenseEmitted(WUMPUS_SMELL) → LocationReported(room 15)
… moves through 16, 17 (SenseEmitted BAT_NEARBY), 16, 20, 13 (BAT_NEARBY) …
ArrowFired → ArrowPathStep ×4 → ArrowHitWumpus
GameEnded(outcome=wumpus_shot) → SessionEnded
```

Every event carries `internal_state_hash` + `rng_cursor` (replay/determinism
substrate) and the harness instrumentation fields (`actor_node`,
`actor_scratchpad`, `tokens_in`/`tokens_out`, `back_prompted`, …) that the
LLM-vs-engine cells will populate. The `.txt` is what the *surface* renders from
these events; the `.jsonl` is the ground truth the harness measures against.
