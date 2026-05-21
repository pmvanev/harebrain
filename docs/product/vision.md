# Vision

The harebrain repo tests one claim: an LLM without a cage drifts; an LLM inside an MPL cage does not. The wager is articulated in [`harebrain.md`](../../harebrain/harebrain.md:14-19) and the experimental program is sketched in [`wumpus_idea.md`](../../wumpus/docs/wumpus_idea.md).

Hunt the Wumpus (Yob, 1973) is the first concrete experiment because it is structurally the entire harebrain pattern minus the brain: a fixed room graph (chart), typed world flags (blackboard), sensed adjacencies (working-memory facts), and a guess-the-verb-shaped decision slot per turn (the LLM seam).

This repository delivers, in dependency order:

1. **A faithful classic Hunt the Wumpus** (`python/packages/wumpus_classic/`) — Yob 1973 rules, byte-recognizable output, seedable for replay, instrumented for harnessing. The current feature.
2. **An MPL chart of the same game** (downstream, separate feature) — same rules, but the chart owns the world state and the LLM consults at decide-leaves via host imports.
3. **The six-cell experiment matrix** (A–F) plus G, the wild baseline — comparing scripted, random, heuristic, harebrain, LangGraph, LangChain, and coding-agent players over N seeded scenarios.
4. **The plots** — divergence events per turn, scaffolding leaks per node, scratchpad accuracy, post-bat recovery turns, arrow-shoot decision quality.

The series writes itself: "the cage works" first (the structural claim, demonstrated on classic Yob), "the brain earns its keep" second (climbing the escalation ladder to find where LLM beats heuristic).

`wumpus_classic` plays three concurrent roles, by design:

| Consumer | Role | What it needs |
|---|---|---|
| Player at a terminal | The game | A CLI that feels like 1973 |
| MPL chart (downstream) | Rule reference | Auditable, line-traceable rules from `wumpus.gwbasic.bas` |
| Experiment harness | Ground-truth oracle | Deterministic seeded replay + structured event stream |

The engine must serve all three from one source of truth. That is why this is a single feature, not three.

## Out of scope for this feature

- MPL integration (separate package, separate feature)
- LLM player implementations (cells D, E, F — separate features)
- Rule extensions: WUMP2 cave variants, WUMP3 hazard variants, escalation-ladder rules L2-L4
- GUI, web port, or graphical map rendering
