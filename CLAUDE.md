# Project conventions

## Development Paradigm

This project follows the **hybrid paradigm**: OOP at the seam, functional core. Concretely:

- The public API surface uses Python-idiomatic OOP (`Game(seed=42).step(action)`)
- Internal state is value-typed (frozen `@dataclass`); transitions are pure functions on values
- No inheritance hierarchies; composition only; `typing.Protocol` for polymorphism points
- The `Game` object is a thin shell over an immutable `World` + a `Random` instance

For implementation, **use `@nw-software-crafter`** (the standard OOP-capable crafter, which handles pure-function modules naturally), not `@nw-functional-software-crafter`.

The paradigm decision is recorded in `docs/feature/wumpus/feature-delta.md` § `## Wave: DESIGN / [REF] ADRs` § ADR-001.

## Mutation Testing Strategy

Mutation testing is a **local developer practice** during slice completion — not a CI gate. Run it locally to find weak spots in the test suite; surviving mutants either get killing tests in the same slice or a documented exemption in `MUTATION_EXEMPTIONS.md`. Kill-rate target: **≥ 80 %** on the slice's modified files (excluding equivalent mutants).

**Tool:** [cosmic-ray](https://github.com/sixty-north/cosmic-ray) — Windows-native, actively maintained. Install: `uv tool install cosmic-ray`. Config lives at `docs/feature/<feature>/deliver/mutation/cosmic-ray.toml`; sessions are kept alongside but gitignored.

Run (from `python/packages/wumpus/`):

```
CONF=../../../docs/feature/wumpus/deliver/mutation/cosmic-ray.toml
SESS=../../../docs/feature/wumpus/deliver/mutation/session.sqlite
uv tool run --from cosmic-ray cosmic-ray init "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray baseline "$CONF"
uv tool run --from cosmic-ray cosmic-ray --verbosity INFO exec "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray dump "$SESS"
```

Cosmic-ray applies + reverts each mutation around the test run — no in-place corruption on interrupt. The current baseline + actionable findings live at `docs/feature/wumpus/deliver/mutation/mutation-report.md`.

**Why not mutmut:** the project's original `[tool.mutmut]` block was written for mutmut 2.x (now unmaintained); mutmut 3.x has no native Windows support ([issue #397](https://github.com/boxed/mutmut/issues/397)) *and* a breaking config-schema rewrite, so it didn't work in either CI (silent no-op) or Docker (config-parse bug). Cosmic-ray is the pragmatic Windows-native alternative. The historical mutmut design lives in `docs/feature/wumpus/feature-delta.md` § DEVOPS / Mutation Testing Configuration (marked superseded).

## Feature documentation convention

The harebrain repo uses the **single-file feature convention**: each feature's wave artifacts (DISCOVER through DELIVER) live inline in `docs/feature/{feature-id}/feature-delta.md`. This includes user stories, journeys, story maps, ADRs, C4 diagrams, CI workflow specs, KPIs — everything.

The standard nWave directory layout (`docs/feature/<feature>/discuss/*.md`, `docs/feature/<feature>/design/*.md`, etc.) is NOT used. Pointer files at the canonical SSOT paths (`docs/product/architecture/brief.md`, `docs/product/journeys/*.md`, `docs/product/kpi-contracts.yaml`) point back to the inline content.

When invoked for a wave, agents:
1. Read the existing `## Wave: <PRIOR> / [REF] ...` sections from `feature-delta.md`
2. Append new `## Wave: <CURRENT> / [REF] ...` sections after the last existing section
3. Do NOT create separate files under `docs/feature/<feature>/<wave>/`
4. Do NOT modify SSOT files at `docs/product/` directly unless explicitly directed (the orchestrator handles that)

## Repository layout

- `python/packages/` — uv workspace packages (wumpus engine + sibling packages)
- `wumpus/` — wumpus-feature scratch space (BASIC source, experiments, design notes)
- `docs/feature/<feature-id>/feature-delta.md` — canonical SSOT for each feature's wave artifacts
- `docs/product/` — product-level SSOT (architecture pointer, journeys, jobs, KPI contracts)
- `docs/research/` — evidence-backed research documents
- `.github/workflows/` — CI workflows (materialized from `## Wave: DEVOPS / [REF] CI Workflows` specs in feature-delta files)

## Active features

| Feature | Wave status | SSOT |
|---|---|---|
| `wumpus` engine | DEVOPS wave complete (2026-05-22); DISTILL pending | `docs/feature/wumpus/feature-delta.md` |
