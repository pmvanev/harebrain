# Wumpus — Mutation testing baseline (2026-05-28)

First-ever real mutation run for the wumpus feature. The CI `mutation.yml` gate
that had previously been the documented quality gate had been **silently
no-op'ing on every push** (uv couldn't find `mutmut` from the workspace root +
the workflow's `|| true` swallowed the spawn failure + `TOTAL=0` was treated
as PASS), so this report is the first time the project actually measured the
test suite's kill rate. The CI workflow has since been retired (commit
`c837315`); mutation testing is now a local developer practice (see
`CLAUDE.md` § Mutation Testing Strategy).

## Run

- **Tool:** [cosmic-ray](https://github.com/sixty-north/cosmic-ray) 8.4.6 (Windows-native; replaces mutmut, which has no native Windows support in 3.x and whose config schema had been rewritten incompatibly with this project's previous `[tool.mutmut]`).
- **Scope (focused first run):** `python/packages/wumpus/src/wumpus/surfaces/mystery.py` only — the smallest new-this-session file (≈ 120 lines), chosen to validate the pipeline end-to-end before scaling up.
- **Test command:** `uv run pytest tests -x --ignore=tests/subprocess -q` (excludes the wexpect smoke that hangs on Windows; matches the project's "NNN non-subprocess tests green" convention).
- **Wall-clock:** ~4 min for 71 mutants (`baseline` 6s + `exec` ~4 min).
- **Config + session DB:** `cosmic-ray.toml` and `session.sqlite` are siblings of this report; `session.sqlite` is gitignored.

## Results

| | count |
|---|---:|
| Total mutants | 71 |
| Killed | 43 |
| **Survived** | **22** |
| Incompetent (cosmic-ray rejected — equivalent / un-compilable) | 6 |
| **Raw kill rate** (`killed / (killed + survived)`) | **66.2 %** |

Raw 66.2 % is below the 80 % target. But the survivors cluster into two distinct buckets, and one of them is genuinely *equivalent* mutants the cosmic-ray default operator set generates against type annotations:

### Survivor analysis

**(A) ~11 survivors are equivalent mutants on type annotations** — the `BitOr_*` replacements (`|` → `+`, `-`, `*`, `/`, `//`, `%`, `**`, `>>`, `<<`, `&`, `^`) all target the `int | None` *return-type annotation* at line 198:

```python
def room_id(self, label: str) -> int | None:
```

Python doesn't enforce type annotations at runtime, so these mutations have no observable behavior — no test could ever kill them. This is a known cosmic-ray default-operator quirk, not a test-suite gap.

**Action:** add these to `MUTATION_EXEMPTIONS.md`, or (better) tune the cosmic-ray operator set to skip annotation mutations on the next run.

**(B) ~11 survivors are a genuine, actionable test gap** in `MysterySurface.terminal_lines` (lines 310–311):

```python
tag = _WIN_TAG if message_kind == "win" else _LOSE_TAG
if reason:
    return (reason, tag)
return (tag,)
```

The 8 comparison mutants on `message_kind == "win"` and the related `AddNot` / `OrWithAnd` survivors all indicate the **Mystery surface's win/lose terminal branch is never exercised by the test suite**. The paired obfuscation property runs short action sequences that don't reach a `GameEnded` event under the Mystery surface, so this whole code path goes untested.

**Action:** add a Mystery-surface acceptance scenario (or extend the paired property) that drives the engine to *both* a win and a loss under `MysterySurface()` and asserts the rendered terminal lines.

### Effective kill rate

Discounting the type-annotation equivalents:

- 43 killed / (43 killed + ~11 real survivors) = **~79.6 %** — one or two killing tests away from the 80 % threshold.

## Recommended follow-ups (own slice or fold into next surface work)

1. **Add Mystery terminal-rendering scenarios** to `R4_surface.feature` (or a sibling property) — drive a forced-win + forced-loss under `MysterySurface()`, assert `terminal_lines` content. Will kill the ~11 `terminal_lines` survivors and push the effective rate well above 80 %.
2. **Tune cosmic-ray operators** — `cosmic-ray operators` lists the available mutators; disable the `BitOr_*` replacements (or any operator that targets annotation syntax) in `cosmic-ray.toml`. Re-run; expect the equivalent-mutant count to drop to ~0.
3. **Expand scope** — re-run with `module-path` widened to the engine + the other surfaces + the new audit (`engine/game.py`, `surfaces/yob.py`, `surfaces/french.py`, `audits/surface_leak.py`). The other modules likely have their own gaps to surface.

## Re-running this report

From `python/packages/wumpus/`:

```bash
CONF=../../../docs/feature/wumpus/deliver/mutation/cosmic-ray.toml
SESS=../../../docs/feature/wumpus/deliver/mutation/session.sqlite
rm -f "$SESS"
uv tool run --from cosmic-ray cosmic-ray init "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray baseline "$CONF"          # sanity check
uv tool run --from cosmic-ray cosmic-ray --verbosity INFO exec "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray dump "$SESS"              # raw results
```

Source files are not modified in place — cosmic-ray applies + reverts each mutation around its test run, so an interrupted run leaves the working tree clean. (Verified post-run: `git status` was clean.)
