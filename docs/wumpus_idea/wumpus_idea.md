# Hunt the Wumpus as the harebrain demo

*A first concrete experiment to test the harebrain bet — three players, one game, an MPL oracle to catch the lies.*

---

## The bet

The harebrain note proposes a wager about long-running LLM agents (`../harebrain/harebrain.md:14-19`): an LLM without a cage drifts, forgets, hallucinates stale-as-fresh, and declares victory early; an LLM inside an MPL cage doesn't. The note even names the analogy explicitly — "the cage was solved in 1980" — citing *Colossal Cave*, *Zork*, and the MUDs, and contrasting them with *AI Dungeon* (`../harebrain/harebrain.md:30-46`).

*Hunt the Wumpus* (Gregory Yob, 1973) is the right first test case. It predates the games the note cites, it is small enough to encode in MPL in a weekend, and it is structurally the entire harebrain pattern minus the brain: a fixed room graph (the chart), typed world flags (the blackboard), sensed adjacencies (working-memory facts), a guess-the-verb-shaped decision slot at every turn (the LLM seam). The demo writes the next paragraph of the article.

## The game, in one screen

Yob's loop is a turn-based prompt cascade. Each turn:

![Yob 1973 prompt loop: a terminal panel shows the player's view — current room, exits, sensed adjacencies, prompts for shoot-or-move and where-to — with arrows out to an LLM-player glyph and back, the LLM acting as the 1973 player who reads text and types commands.](images/fig-02-prompt-loop.svg)

Two top-level prompts (`S or M`, then `where to?` or an arrow path of up to 5 connected rooms). Senses print passively on entry. The 1973 game already prevents illegal world moves — "move to room 999" returns `NOT CONNECTED`. It does not trust the player.

This matters for the experimental design. The cage we are testing is *not* "does the LLM make moves the game would reject" — Yob's game rejects those for everyone. The cage is about something subtler: whether the LLM's *internal model of the world* stays honest over a long enough run.

## Two architectures

The cleanest comparison isn't "all three players talk to the same MPL game and we count illegal moves" — Yob's game would catch those for everyone and the comparison would be uninteresting. The cleaner comparison runs the LangChain and LangGraph agents as *trusted narrators* — told the rules of Wumpus and asked to play through, owning the world model in their own context — while an MPL Hunt the Wumpus runs silently in parallel as a ground-truth oracle. Per turn, a diff flags every divergence. The harebrain version is the only one where MPL is *in* the loop, with the LLM consulted at decision leaves via host imports.

![Two architectures side-by-side. Left panel labeled 'LangChain / LangGraph (E, F)': trusted-narrator LLM owns the world model in its own context, MPL Hunt the Wumpus runs silently in parallel as oracle, per-turn diff produces divergence events. Right panel labeled 'harebrain (D)': MPL chart is the world, with a decide-leaf host import calling the LLM for per-turn verdicts that rules route on; blackboard holds typed sensed-room slots with decay.](images/fig-01-two-roles.svg)

> **Why this split.** Asking an LLM to "be the game and the player" is the *AI Dungeon* failure mode the note calls out by name (`../harebrain/harebrain.md:46`). It's the right failure mode to put on display, because that's the foil the cage exists to outdo. Letting LangChain/LangGraph play *against* a real game would silently fix half their problems for them.

So MPL appears in exactly one role per run, but the role is different:

| Run | MPL's role | Where the world state actually lives |
|---|---|---|
| E, F (LangChain, LangGraph) | **External oracle** — referee, watches, diffs | Inside the LLM's context |
| D (harebrain) | **Internal cage** — chart owns rooms, vars, rules | Inside the chart's Manifest |

The agent in E and F *can* lie about world state. The agent in D *cannot* — not because we forbid it but because it doesn't own state to lie about. The chart owns the Manifest; the LLM returns verdicts and the chart routes on them. An LLM verdict like `"move_to_99"` simply doesn't match any rule from the current room and the transition doesn't fire.

## What gets compared

The oracle gives us a sharp per-turn metric the prose-only architectures couldn't otherwise produce. For each turn of an E or F run:

- **Claimed state** — what the LLM's narration says is true (current room, sensed adjacencies, kills, inventory)
- **Oracle state** — what the MPL ledger says is true after replaying the same move from the same seed
- **Divergence event** — any field that disagrees, with turn number and field name

A divergence is the agent screwing up. Examples expected from the note's failure-mode catalogue:

- *Resurrected entity* — "you killed the wumpus on turn 9 ... you smell a wumpus" on turn 17
- *Inventory drift* — "I'll shoot another arrow" when the oracle says arrows are 0
- *Position confusion* — bat-teleport on turn 12 narrated as still-in-room-8
- *Stale belief acted on* — agent moves toward a wumpus smell that predates a shot that startled the wumpus

For D (harebrain), the same metric is degenerate by construction: claimed and actual are the same thing because there's no separate "claim." That asymmetry *is* the structural payoff. Where the cage exists the divergence count is structurally zero; where it doesn't, the divergence count is whatever it is and that's the data we wanted.

## The experiment matrix

Six runs over N seeded scenarios — three controls, three comparisons:

![Six-cell experiment matrix in two rows. Top row 'controls (no LLM)' holds A scripted, B random-legal, C heuristic — all playing the same MPL game with no LLM. Bottom row 'LLM players' holds D harebrain (LLM at MPL leaf via host import, blackboard prompts), E LangGraph (idiomatic agent, graph state, transcript), F LangChain (bare ReAct, transcript only). Two comparison arrows: a vertical 'brain earns keep?' between C and D, and a horizontal 'cage helps?' across D, E, F.](images/fig-03-experiment-matrix.svg)

The controls (A, B, C) all play the *same* MPL Hunt the Wumpus — they validate that the chart faithfully encodes Yob. C also serves as the **ablation**: a non-LLM brain inside the cage. If C wins games at nearly the same rate as D, the cage was doing the work and the brain wasn't pulling weight in this game — which is itself a real finding.

The comparisons are the two questions the matrix exists to answer:

- **C ↔ D — does the brain earn its keep?** A small Python heuristic ("avoid smelled rooms, count arrows, triangulate before shooting") versus an LLM in the same cage. If D ≫ C, the brain is doing real work. If D ≈ C, classic Wumpus is too small to surface the brain's contribution.
- **D ↔ E, F — does the cage help?** The harebrain agent versus the same LLM in two progressively-less-caged configurations. We expect D to have zero divergence events by construction and E/F to accumulate them at meaningfully different rates.

## What "smarter" actually means

Aggregate win-rate is the noisiest possible measure. Sharper:

| Metric | What it captures | Where it shows |
|---|---|---|
| Win rate over N seeds | Aggregate — easy to read, slow to convince | Bar chart across A–F |
| Turns to victory (winning runs only) | Efficiency — does the brain find the wumpus faster? | Boxplot per implementation |
| Variance across seeds | Robustness — does the brain handle awkward boards a heuristic stumbles on? | Spread of the boxplot |
| **Divergence events per run** | The headline metric — how often does the trusted narrator lie? | Line: cumulative divergences vs turn |
| **Arrow-shoot accuracy** | Per-decision: given smell history, was the path optimal? | Per-decision bar, segmented by implementation |
| Tokens per turn | What the cage costs vs. what it saves | Line: tokens vs turn |

The **divergence-events** metric is the one the audit architecture buys us that nothing else does. It's also the one that maps directly onto the harebrain.md failure-mode catalogue: each divergence has a *kind* (resurrected, inventory, position, stale-belief), and the per-kind counts tell you which payoff of the cage is doing the most work.

The **arrow-shoot decision** is the most likely seam where the LLM beats the heuristic in classic Wumpus. Move decisions are mostly "don't enter rooms with bad senses" — a heuristic eats that. But shooting is multi-room backward inference from sensed history, and a crooked-arrow path is a sequence under uncertainty. That's where the brain plausibly earns its keep.

## Honest framing: cage demo first, brain demo second

Classic Yob 1973 is probably the *cage* demo, not the *brain* demo. The state space is small enough that a careful heuristic plays well, and the LLM may not pull meaningfully ahead in aggregate wins. That's not a problem if we sequence the experiments deliberately.

![Escalation ladder: four stages left to right, each labeled with which harebrain payoff it isolates. L1 Classic Yob (1973 rules, fixed dodecahedron) probes chart topology and the structural 'no illegal executions' claim; L2 Wumpus moves when startled probes blackboard slots and working-memory-fact decay; L3 Partial observability (only senses visible on entry) probes prompt construction; L4 Bigger or non-dodecahedron graph probes topology generalization. Arrows step from each stage to the next; caption notes 'don't escalate until C falls short'.](images/fig-04-escalation-ladder.svg)

Each step on the ladder isolates a *specific* payoff from `../harebrain/harebrain.md` — and each is reachable from the *same* MPL chart by adding rules, not by rewriting the demo. That's the diagnostic-surface promise from the note materializing: *"every drift is locatable to a state, every memory loss to a fact decay rate"* (`../harebrain/harebrain.md:236`).

The framing for the series, if all of this pays off:

- **Note 1: "The cage works."** Classic Wumpus. A–F runs. Headline metric: divergence events per run. Expected result: D = 0 by construction, E and F nonzero, with characteristic per-kind distributions; A, B, C as control sanity. Validates the structural claim.
- **Note 2: "The brain earns its keep."** Whichever escalation (L2 most likely) first surfaces a measurable gap between D and C on a specific decision class. Validates the cooperative claim.

That progression matches the article: the four payoffs are *separable*, not a single monolithic bet (`../harebrain/harebrain.md:48-110`). Demonstrating them one at a time, with an experimental design that isolates each, is more convincing than one run trying to show everything.

## What to build first

The pragmatic first cut, in five steps:

1. **Spike the host import.** Smallest possible MPL chart with one host import returning a stub verdict, wired into Python. Prove `python/packages/harebrain/` can depend on (or path-import) `lostinplace/mplv2/` and round-trip a tick. This is the only real unknown.
2. **MPL Hunt the Wumpus.** Twenty rooms, fixed dodecahedron, hazards, senses, arrow physics. Drive it from `runs/wumpus.py` like the `host_calls/host_calls_demo.py` example. Run A (scripted) until the chart is right.
3. **Controls.** Add B (random-legal) and C (heuristic). Now we have a baseline.
4. **The three LLM players.** D wires the LLM into the chart's decide-leaf as a host import. E and F take the rules-and-board prompt and narrate; the oracle harness replays their moves through the chart and emits divergence events. Same seeds across all three.
5. **The plots.** One Jupyter notebook reads ledgers + divergence logs and produces the six measurements above. Identical templates for the two notes.

Then measure one thing: **does the trusted narrator lie?** And if it does, **which kind of lie**? Compared to "the agent went sideways and we don't know where," that's already a better foundation (`../harebrain/harebrain.md:236`).

If it works, the cage scales by climbing the escalation ladder. If C ≈ D at L1 *and* at L2, the brain claim weakens and we learn — honestly — that this game class is too shallow for harebrain's full thesis, and we'd need a workflow closer to the top three rows of the harebrain tradeoff table (`../harebrain/harebrain.md:213-222`) to test it properly. Either outcome moves the needle.

## Where this sits in the series

This note sketches the experiment that follows from the synthesis.

| Source | What it contributes |
|---|---|
| [Harebrain, sketched](../harebrain/harebrain.md) | The thesis being tested, the four payoffs, the failure-mode catalogue |
| [MPLv2 vs. Harel](../mpl/mpl.md) | The runtime — host imports, Manifest, ledger, snapshots |
| [Traditional Game AI Primitives](../game-ai/game-ai.md) | The blackboard and working-memory-fact patterns the cage borrows |
| [SBIR proposal as a harebrain chart](../sbir_idea/sbir_idea.md) | The other application sketch; this one is the *experimental* counterpart |

---

**Sources.** Yob, G., "Hunt the Wumpus" (1973), originally published in *People's Computer Company*. Russell, S. & Norvig, P., *Artificial Intelligence: A Modern Approach* — uses Wumpus as the canonical knowledge-representation example. Orkin, J., "Three States and a Plan: The AI of F.E.A.R." GDC 2006 — working-memory facts. `github.com/lostinplace/mplv2` — runtime, host imports, ledger, snapshots. All figures original SVGs drawn for this note.
