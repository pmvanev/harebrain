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

## Research summaries

`docs/research-summaries/<slug>/` holds **research summaries** — the repo's term for an opinionated, house-style distillation of one external paper or article. A research summary is *not* a neutral abstract. It (a) extracts the load-bearing ideas in the project's voice, (b) redraws the source's key diagrams in the harebrain visual language, and (c) maps the work back onto the **harebrain hypothesis** (`harebrain = fast LLM brain × structured game-AI cage`). Use `docs/research-summaries/llm-modulo/` as the canonical template.

**When the user says "make me a research summary on X":** resolve X to its source, create `docs/research-summaries/<slug>/`, and follow the template below. If X is downloadable (an arXiv paper, a public PDF), fetch it into the folder — for arXiv, `https://arxiv.org/pdf/<id>` → save as a descriptive filename. Read the full source before writing.

Directory shape:

- `<slug>/<slug>.md` — the summary
- `<slug>/images/glyph.svg` — masthead glyph
- `<slug>/images/fig-0N-*.svg` — original figures redrawn for the page
- `<slug>/<descriptive-name>-<arxiv-id>.pdf` — the source PDF when one exists

`.md` structure (mirror an existing summary):

1. masthead line: `![alt](images/glyph.svg)`
2. `# <Title>, *<gerund>*` — the gerund is the house tic (*distilled*, *redrawn*, *graded*, *audited*, *composed*, *staged*)
3. an italic subtitle line naming the source and its tie to harebrain
4. a `---` rule
5. opinionated body — prose, tables, `> **callout.**` blockquotes, and the redrawn figures inline with italic captions
6. a `## Where this sits in the harebrain hypothesis` section anchored by a two-column mapping figure (source constructs ↔ harebrain primitives)
7. a `**Sources.**` footer: full citation, arXiv id, and a link to the local PDF

**SVG conventions** (theme-adaptive — see the [[harebrain-md-layout]] memory and any existing `glyph.svg`):

- Class-based `currentColor` + an `@media (prefers-color-scheme: dark)` block. Never hardcode a single-mode palette — Phil reads markdown in dark mode locally.
- Reference SVGs as `<img>` via markdown `![]()`. GitHub's sanitizer strips inline `<svg>`; loading via `<img>` preserves the embedded `<style>`/media query.
- Palette tokens (light / dark): ink `#1a1810`/`#ede2c4`, muted `#5d553f`/`#a89c7d`, **oxblood** `#8b1f2c`/`#e09098` (the external/source side), **blueprint** `#1f4f7a`/`#88c0e8` (the harebrain side), sage `#4f6b3f`/`#b1c98c`, plus `*-tint` fills at ~6–10 % alpha.
- Fonts: `Fraunces, serif` for headings/labels (often `font-style="italic"`), `JetBrains Mono`/`ui-monospace` for code-ish labels.

## Repository layout

- `python/packages/` — uv workspace packages (wumpus engine + sibling packages)
- `wumpus/` — wumpus-feature scratch space (BASIC source, experiments, design notes)
- `docs/feature/<feature-id>/feature-delta.md` — canonical SSOT for each feature's wave artifacts
- `docs/product/` — product-level SSOT (architecture pointer, journeys, jobs, KPI contracts)
- `docs/research/` — evidence-backed research documents
- `docs/research-summaries/<slug>/` — house-style distillations of external papers (see § Research summaries)
- `.github/workflows/` — CI workflows (materialized from `## Wave: DEVOPS / [REF] CI Workflows` specs in feature-delta files)

## Active features

| Feature | Wave status | SSOT |
|---|---|---|
| `wumpus` engine | DELIVER nearly complete (2026-06-10) — all slices R0–R5 shipped incl. R5-S01 host-import (engine-side, via MPL spike); done-criterion #3b (real MPL binding) deferred. Pending: mutation testing + finalize. | `docs/feature/wumpus/feature-delta.md` |
