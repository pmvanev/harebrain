# Hunt the Wumpus — runnable BASIC source

The 1973 Gregory Yob source, set up to run from the Windows command line via PC-BASIC.

This directory exists for the **G — wild baseline** experiment cell (`../../wumpus_idea.md:97-103`), where a general-purpose coding agent is handed a working CLI Wumpus and told to play it. The same files double as the canonical reference for the rules of the game and (for `wumpus.bas` specifically) as the primary-source citation for the article.

## Files

| File | Purpose |
|---|---|
| `wumpus.bas` | Canonical Yob source. Fetched from kingsawyer/wumpus on GitHub; the only edit from upstream is removing the `PROGRAM LISTING` header line, which was a printed-listing artifact and not BASIC. |
| `wumpus.gwbasic.bas` | Same program, with 14 lines patched to run under GW-BASIC dialect (PC-BASIC's target). This is the file you actually run. |
| `patches.diff` | Unified diff between the two — auditable record of every dialect change. |
| `README.md` | This file. |

## Provenance of `wumpus.bas`

Fetched from:

```
https://raw.githubusercontent.com/kingsawyer/wumpus/main/wumpus.basic
```

Cross-verified byte-identical with `WECMuseum/hunt_the_wumpus`. Both carry the original Ahl-anthology header (`REM- HUNT THE WUMPUS / REM: BY GREGORY YOB`) and Ahl's editorial `ADDED BY DAVE` note at line 0052.

## Why two `.bas` files

Yob wrote this for HP 2000 timesharing BASIC, which differs from Microsoft GW-BASIC (PC-BASIC's target dialect) in a few load-bearing ways. Running `wumpus.bas` unmodified under PC-BASIC fails on:

- **`RND(0)`** — HP returns the next random number; GW-BASIC returns the *last* one (no advance). 3 occurrences, all in `DEF FN` helpers.
- **`GOTO <expr> OF n1, n2, ...`** — HP's computed GOTO syntax. GW-BASIC writes the same thing as `ON <expr> GOTO n1, n2, ...`. 2 occurrences.
- **`#` for not-equal** — HP uses `#`; GW-BASIC uses `<>`. 8 occurrences across 8 lines (some lines have multiple).
- **`RETURN!`** at line 3330 — almost certainly a typo in the original Ahl-anthology copy (the `!` is not valid in any BASIC dialect there). Dropped.

`wumpus.gwbasic.bas` applies these 14 edits and nothing else. The diff is in `patches.diff`. No gameplay logic was touched.

If you want literally byte-equivalent Yob, install **vintage-basic** instead (Lyle Kopnicky's Haskell interpreter, purpose-built for the Ahl anthology). It runs `wumpus.bas` unmodified. PC-BASIC was chosen here because `pip install pcbasic` is the lowest-friction install on Windows once the Python version issue (below) is sorted.

## Install

System Python on this machine is 3.14, but PC-BASIC 2.0.7 imports `chunk` from the standard library, which was removed in Python 3.13. We install PC-BASIC into an isolated tool environment with Python 3.12:

```powershell
uv tool install --python 3.12 pcbasic
```

This puts a `pcbasic` shim on PATH that runs against a private 3.12 interpreter. No change to system Python.

## Play

```powershell
pcbasic --interface=text wumpus.gwbasic.bas
```

`--interface=text` runs in your existing terminal — no SDL window opens. Input is line-buffered: type your command and press Enter.

A typical session:

```
INSTRUCTIONS (Y-N)? N
HUNT THE WUMPUS

I SMELL A WUMPUS!
YOU ARE IN ROOM  8
TUNNELS LEAD TO  1  7  9

SHOOT OR MOVE (S-M)? M
WHERE TO? 7
...
```

To quit mid-game, Ctrl-C.

## Caveats

- **Dialect patches are minimal but real.** If the article claims literal Yob fidelity, cite the patch diff alongside. The patches are mechanical translations between equivalent BASIC dialects — no gameplay logic changed — but they are edits.
- **No seeding.** Yob's source doesn't `RANDOMIZE`, so PC-BASIC's RNG starts from whatever state its interpreter initializes to. For reproducible experiment runs (later), insert a `5 RANDOMIZE <seed>` line at the top. Document it as a controlled deviation.
- **Windows + `pexpect` later.** When the experiment harness wires an LLM to this game, the standard `pexpect` package won't work on Windows (no real pty). Use `wexpect` instead — drop-in API.

## See also

- [`../pure_llm_trust.md`](../pure_llm_trust.md) — the first experiment that uses the rules captured here (DM-LLM imitates this program's I/O).
- [`../../wumpus_idea.md`](../../wumpus_idea.md) — parent note. Cell G described at line 97-103, build step 6 at line 151.
