# Wumpus II and III — the sequels Yob wrote

*What changed after the 1973 dodecahedron, and why Wumpus II is the historical precedent for the L4 escalation rung.*

---

## Why this note exists

Everything else in `wumpus/` is about Yob's *original* 1973 *Hunt the Wumpus* — twenty rooms, a fixed dodecahedron, two bats, two pits, one wumpus, five crooked arrows (`wumpus_idea.md`, `wumpus_python_goals.md:54`). That is the right first test case and stays the baseline. But the escalation ladder (`wumpus_idea.md:160-164`, `fig-04-escalation-ladder.svg`) names an **L4 — "bigger or non-dodecahedron graph"** rung whose job is to probe *topology generalization*. Yob already built that rung in 1975. It's called **Wumpus II**, and the cave types it ships are a ready-made menu of non-dodecahedron topologies — including some genuinely adversarial ones (one-way tunnels, self-loops, a torus). Documenting it here keeps us honest: L4 isn't a new idea we're inventing, it's a 50-year-old game we can lift the maps from.

## Wumpus II — same rules, choose your cave

Yob wrote Wumpus II immediately after the original. The gameplay is unchanged — the hazards, the senses-on-entry, the `S`/`M` prompt, the up-to-five-room crooked-arrow path are all identical. The one addition is a **map menu at startup**: instead of the dodecahedron always, you pick the cave's *topology*. That single change is the whole point of the sequel.

The menu offers seven choices:

| # | Cave | Topology | Regular? |
|---|------|----------|----------|
| 1 | **Dodecahedron** | The original 1973 graph — 20 rooms, every room has exactly 3 two-way tunnels | regular |
| 2 | **Möbius strip** | Two rows of ten (`20-18-…-2` / `19-17-…-1`) joined with a half-twist so room 2 ↔ 19 and room 1 ↔ 20 | regular |
| 3 | **String of beads** | A linear chain of rooms; pit placement can produce impossible (unwinnable) boards | regular |
| 4 | **Hex network (torus)** | 20 intersection points on a rectangle, left/right edges joined into a cylinder, then top/bottom joined into a torus — a honeycomb stretched onto a doughnut | irregular |
| 5 | **Dendrite with degeneracies** | A branching tree full of dead-ends; a single pit can wall off whole regions | irregular |
| 6 | **One-way lattice** | Tangled layout where tunnels are *directed* — entering a room doesn't mean you can go back the way you came | irregular |
| 7 | **Build your own** | Player types in their own adjacency table | — |

The first three are "normal" caves in Yob's sense — every room has three tunnels and every tunnel carries two-way traffic, so they behave like the original even where the shape differs. The irregular caves break those guarantees: **one-way tunnels**, **tunnels that loop a room back to itself**, and uneven degree. Yob rated the hex/torus net the closest in challenge to the original dodecahedron and the dendrite the worst (too easily blocked by one unlucky pit).

**Publication.** Originally distributed through the *People's Computer Company* shortly after the 1973 game (c. 1975–76); the widely-cited reprint is *The Best of Creative Computing, Volume 2* (1977), p. 244 — the scanned page the request started from. Exact first-printing dates vary by source, so treat the year as approximate.

## Wumpus III — moving hazards (attribution uncertain)

A third game in the lineage adds **motion**: the bats, pits, and wumpus all relocate randomly each turn rather than sitting still, so a board that looks safe this turn can trap you the next — "more opportunities to get trapped in an unwinnable position." It also introduces **Tumareos**, arrow-eating creatures that can swallow a shot in flight, and sticks to the single dodecahedron layout. Note the attribution is murky: some sources credit a "Howard" (not Yob) from a 1974 PCC Games booklet rather than Yob himself. We don't rely on Wumpus III for anything here; it's logged for completeness.

## How this maps onto the harebrain experiment

- **L4 escalation (`wumpus_idea.md:160-164`).** Wumpus II's menu *is* the L4 rung. When we want a non-dodecahedron graph to test topology generalization, we don't invent one — we encode one of Yob's maps. The torus (hex net) is the natural first pick: comparable difficulty to the dodecahedron but a different shape, so a model can't lean on a memorized canonical adjacency table.
- **Phantom-geography divergences (`wumpus_idea.md:59`).** The irregular caves are purpose-built to expose the *"narration treats room X and Y as connected when the graph disagrees"* failure mode. **One-way tunnels** are the sharpest case: an LLM narrator that assumes tunnels are symmetric (because the dodecahedron's always were) will hallucinate a return path the directed graph never granted. The MPL chart, owning the adjacency table, simply won't fire the reverse transition — exactly the structure-vs-suggestion contrast the demo exists to show.
- **Obfuscation, complementary to Mystery Wumpus (`wumpus_idea.md:134`).** Mystery Wumpus relabels *strings* while keeping the topology byte-identical. Wumpus II does the opposite — keeps the rules and surface vocabulary but changes the *topology*. Together they separate two things training-corpus retrieval could be leaning on: the canonical room names and the canonical room graph.
- **Engine fit (`wumpus_python_goals.md:101`).** The goals doc already requires escalation levels to be *additive over the same base engine* — "adding a rule must not require rewriting the rest." Swapping the adjacency table for a Wumpus II map is the cleanest possible instance of that: same engine, different `DATA`.

---

**Sources.** Yob, G., "Hunt the Wumpus II," reprinted in *The Best of Creative Computing, Volume 2* (1977), [p. 244](https://www.atariarchives.org/bcc2/showpage.php?page=244). [Renga in Blue, "Before Adventure, Part 5: Wumpus 2 and 3"](https://bluerenga.blog/2019/04/05/before-adventure-part-5-wumpus-2-and-3/) — cave-by-cave breakdown and Yob's own rankings. [Wumpus II (1975) — MobyGames](https://www.mobygames.com/game/46556/wumpus-ii/). [Hunt the Wumpus — Wikipedia](https://en.wikipedia.org/wiki/Hunt_the_Wumpus). [Wumpus 2 — Internet Archive (QB64 port)](https://archive.org/details/wumpus2.qb64). [Koumbaya/wumpus](https://github.com/Koumbaya/wumpus) — a Go implementation of Wumpus I, II, and III with the alternate maps.
