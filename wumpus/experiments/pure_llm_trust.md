# Pure LLM trust — the cageless baseline

*Two LLMs in a room with a copy of the rules. One declares itself the dungeon master. One declares itself the player. Nothing else. The simplest possible test of what happens when the cage is not just thin but absent.*

---

## Where this sits

The parent note proposes a six-cell matrix (`../wumpus_idea.md:82-95`) in which MPL appears in *some* role for every LLM run — internal cage in D, external oracle in E and F. This experiment is the cell *before* the matrix: no MPL anywhere, no agent framework, no tools. Two model invocations alternating in a loop with a shared rules document.

It's the *AI Dungeon* configuration the parent note names as the failure-mode foil (`../wumpus_idea.md:29`). The reason to run it first is exactly that — if the failures it produces aren't there, the rest of the matrix is solving a non-problem.

## Setup

Three pieces:

- **`rules.md`** — Yob's 1973 game spec: twenty rooms in a fixed dodecahedron, two bats, two pits, one wumpus, five arrows, sense rules on entry, the `S`/`M` prompt and the up-to-five-room arrow path. The only world-knowledge either model gets, byte-identical for both sides.
- **DM system prompt** — "You are the Hunt the Wumpus game. The rules are below. Generate a fresh cave layout and hazard placement, then present the player's opening view in the prompt format from the rules. Maintain the world state across turns. Reject illegal moves."
- **Player system prompt** — "You are playing Hunt the Wumpus. The rules are below. The dungeon master will prompt you. Respond with one command per turn in the format from the rules."

The harness is a Python loop: send the DM's last message to the player, send the player's reply to the DM, append both to a transcript, repeat until the DM declares game over or a turn cap fires. No tools, no graph, no scratchpad, no oracle. Both models hold their respective halves of the state machine entirely in their own context.

## What this measures, day one

Without an oracle, the **divergence-events** metric from the parent note (`../wumpus_idea.md:46-61`) is not directly computable — there is no ground truth to diff against. But several metrics still apply unchanged from transcript inspection alone:

- **Turns to terminal state** — does either model recognize when the game should end?
- **Scaffolding leaks, degenerate form** — the DM has exactly one role; does it stay in it, or slip into playing for the player, narrating from the player's POV, or refusing to commit to state?
- **Reasoning unfaithfulness** — the player narrates "I'll avoid room 7 because of the draft" then commands `M 7`. Visible without an oracle.
- **Internal contradiction** — DM says "you smell a wumpus" on turn 4 in room 8, then on turn 9 claims the wumpus is and always has been in room 14, where the dodecahedron edges make turn-4 impossible. Catchable from the transcript alone.

These are not the full failure-mode catalogue from the parent note — they are the subset *visible without an oracle*. That's the point of running this first: it should be enough to convince a reader the cageless case fails badly, before any of the MPL infrastructure exists.

## What this measures, day two

Once the MPL chart exists (step 2 in the parent note's build order, `../wumpus_idea.md:147`), the same transcripts gain a second layer of analysis: replay the player's moves through the chart from the same starting layout the DM claims to have used, and diff. This retroactively produces the **divergence-events** stream on the existing transcripts — no re-running needed.

The "same starting layout" piece is the catch. The DM's opening message has to disclose the cave layout and hazard placement in a parseable form, or the replay can't reconstruct the world. The cleanest way: require the DM to emit a JSON block in its first message describing the generated cave, before any narration. The player never sees that block — the harness strips it before forwarding. The replay tool reads it.

If the DM refuses to commit to a layout up front and instead invents geography turn-by-turn, that is itself a finding, and one of the exact failure modes the cage exists to outdo.

## What we expect

From the harebrain failure catalogue (`../../harebrain/harebrain.md:14-19, 30-46`), predicted DM failures:

- *Resurrected wumpus* — declared dead on turn 9, smelled again on turn 17
- *Phantom geography* — turn 4's adjacencies inconsistent with turn 9's claim about the same room
- *Inventory drift* — player has fired six arrows in a five-arrow game
- *Generation-on-the-fly* — refusing to commit upfront, inventing the cave to fit current narrative needs
- *Senses that don't match position* — drafts in rooms not adjacent to pits

Predicted player failures:

- *Stale belief acted on* — moves toward a smell that an earlier failed shot should have moved
- *Reasoning unfaithfulness* — argues for room 3, commands room 7
- *Format violations* — narrates a move instead of emitting the command verb

Both lists map directly onto rows of the divergence and leak metrics in the parent note (`../wumpus_idea.md:52-59, 67-74`). The expected finding from this experiment: every one of those is observable in raw transcripts.

## Why this is worth running before the rest

1. **It motivates the rest of the matrix.** If a reader sees a transcript where the DM resurrects the wumpus three times in twenty turns, the structural argument for the cage stops needing to be argued.
2. **It's cheap.** Two model calls in a loop. No MPL, no LangGraph, no tools. A weekend at most.
3. **It calibrates the oracle.** When the MPL chart exists, transcripts are already on disk ready to replay. The first oracle output is *already* the headline plot.
4. **It bounds the worst case.** The other LLM cells in the matrix (E, F) at least get to *check* the world via the oracle-as-referee in some runs. This cell has no referee at all. Whatever happens here is the floor of how bad cageless agents get.

## Build order

1. Write `rules.md` from the 1973 spec. Include exact I/O format and sense rules — both models need them to converge.
2. Write the DM and player system prompts. Iterate on the DM prompt until it reliably emits the cave-disclosure JSON block on turn 0 and stays in role across long runs.
3. Write the loop: two `messages.create` calls per turn, append-only transcript log, turn cap, terminal-state regex.
4. Run N seeded scenarios. Seed varies the random numbers fed *into* the DM prompt for layout generation, since the model itself isn't seedable. N = 20 is plenty here.
5. Hand-annotate the first ten transcripts for the failure modes above. The annotations become the regression cases for the automated divergence-events pass once the MPL chart exists.

## Sits next to

| Source | Relation |
|---|---|
| [Hunt the Wumpus as the harebrain demo](../wumpus_idea.md) | The parent note. This experiment is the cell-before-the-matrix it doesn't otherwise include. |
| [Harebrain, sketched](../../harebrain/harebrain.md) | The thesis being tested, the failure-mode catalogue. |
