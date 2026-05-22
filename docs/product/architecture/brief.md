# Architecture SSOT pointer

The harebrain repo uses the **single-file feature convention**: each feature's wave artifacts (DISCOVER through DELIVER) live inline in `docs/feature/{feature-id}/feature-delta.md`. This includes architecture content (C4 diagrams, ADRs, component sketches, paradigm decisions).

This `docs/product/architecture/brief.md` file is therefore a **pointer**, not a mirror. It exists so consumers of the standard nWave directory layout (architects, reviewers, downstream agents) can find architecture content via the conventional path even though the canonical SSOT lives elsewhere.

## Current feature architectures

| Feature | Status | Canonical SSOT |
|---|---|---|
| `wumpus` engine | DESIGN wave complete (2026-05-22) | [`docs/feature/wumpus/feature-delta.md`](../../feature/wumpus/feature-delta.md) — see sections beginning at `## Wave: DESIGN / [REF] ...` |

## What lives in each feature's `## Wave: DESIGN / [REF] ...` sections

Per the harebrain convention, a feature's DESIGN wave produces these inline subsections:

- `[REF] Phase Tracker` — phase status table
- `[REF] Inputs Consulted` — reading checklist
- `[REF] Quality Attributes` — ranked quality attributes + constraints + existing-system findings
- `[REF] Tech Stack` — language, build tool, dataclass lib, etc., with rationale
- `[REF] Paradigm` — OOP / FP / hybrid, with the crafter-agent routing implication
- `[REF] C4 Context` — Mermaid C4Context diagram
- `[REF] C4 Container` — Mermaid C4Container diagram
- `[REF] Component Sketch` — L3 component view + module dependency direction
- `[REF] Tier A type definitions` — the type designs locked in DESIGN
- `[REF] Engine module layout` — concrete module/file plan with dependencies
- `[REF] ADRs` — all ADRs inline (one section per ADR)
- `[REF] Wave Decisions Summary` — formatted per the `/nw-design` command's template
- `[REF] Handoff Package` — what each downstream wave reads first

## ADRs

Per the harebrain single-file convention, ADRs are **inlined under `[REF] ADRs`** in each feature's `feature-delta.md`. They are NOT split into separate `adr-*.md` files.

ADRs for the `wumpus` feature land at `docs/feature/wumpus/feature-delta.md` § `## Wave: DESIGN / [REF] ADRs` — ADR-001 through ADR-010.

If a future ADR has cross-feature implications (e.g., a workspace-wide convention), it gets a stub file in `docs/product/architecture/adr-*.md` that points to the canonical feature's inline ADR.

## C4 diagrams

Per the same convention, C4 diagrams (Context, Container, Component) live inline. The Mermaid syntax is in the feature-delta file; rendering happens wherever Mermaid is rendered (GitHub, Obsidian, mkdocs).

If a future feature needs cross-feature C4 diagrams, those can live at `docs/product/architecture/c4-system.md` as a standalone artifact.

## Changelog

- 2026-05-22 — Bootstrapped. `wumpus` engine DESIGN wave completes; pointer added.
