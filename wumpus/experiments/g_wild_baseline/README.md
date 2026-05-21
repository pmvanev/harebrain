# Hunt the Wumpus — runnable BASIC source

The 1973 Gregory Yob source, set up to run from the Windows command line via PC-BASIC.

This directory exists for the **G — wild baseline** experiment cell (`../../docs/wumpus_idea.md:97-103`), where a general-purpose coding agent is handed a working CLI Wumpus and told to play it. It also doubles as the canonical reference for the rules of the game.

## Files

| File | Purpose |
|---|---|
| `wumpus.gwbasic.bas` | Yob's source with 14 lines patched to run under GW-BASIC dialect (PC-BASIC's target). The file you actually run. |
| `patches.diff` | Unified diff against upstream — auditable record of every dialect change. |
| `README.md` | This file. |

## Provenance

Starting point — Gregory Yob, *Hunt the Wumpus*, 1973, as preserved in the kingsawyer mirror:

```
https://raw.githubusercontent.com/kingsawyer/wumpus/main/wumpus.basic
```

Cross-verified byte-identical with `WECMuseum/hunt_the_wumpus`. Both carry the original Ahl-anthology header (`REM- HUNT THE WUMPUS / REM: BY GREGORY YOB`) and Ahl's editorial `ADDED BY DAVE` note at line 0052. The only edit applied before the dialect patches was removing the upstream `PROGRAM LISTING` header line — a printed-listing artifact, not BASIC.

## Why we patched

Yob wrote this for **HP 2000 timesharing BASIC**, which differs from Microsoft GW-BASIC (PC-BASIC's target dialect) in a few load-bearing ways. The upstream source won't even tokenize under PC-BASIC. `patches.diff` records all 14 edits, all mechanical translations between equivalent dialects — no gameplay logic was touched. The categories:

| Issue | HP 2000 | GW-BASIC | Count |
|---|---|---|---|
| RNG advance | `RND(0)` — returns next number | `RND(0)` — returns *last* number (no advance); use `RND(1)` to advance | 3, all `DEF FN` helpers |
| Computed GOTO | `GOTO <expr> OF n1, n2, ...` | `ON <expr> GOTO n1, n2, ...` | 2 |
| Not-equal operator | `#` | `<>` | 8 lines (some lines have multiple) |
| Typo in Ahl-anthology copy | `RETURN!` at line 3330 — the `!` is not valid BASIC in any dialect | `RETURN` | 1 |

That last one is almost certainly a transcription artifact from the printed Ahl anthology, not anything Yob wrote.

If you want literally byte-equivalent Yob with no patches, install **vintage-basic** instead (Lyle Kopnicky's Haskell interpreter, purpose-built for the Ahl anthology). It runs the upstream source unmodified. PC-BASIC was chosen here because `uv tool install --python 3.12 pcbasic` is the lowest-friction install on Windows.

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
- [`../../docs/wumpus_idea.md`](../../docs/wumpus_idea.md) — parent note. Cell G described at line 97-103, build step 6 at line 151.
- [`../../README.md`](../../README.md) — repo-level install (uv project + `pcbasic` tool).
