# Project conventions

## Development Paradigm

This project follows the **hybrid paradigm**: OOP at the seam, functional core. Concretely:

- The public API surface uses Python-idiomatic OOP (`Game(seed=42).step(action)`)
- Internal state is value-typed (frozen `@dataclass`); transitions are pure functions on values
- No inheritance hierarchies; composition only; `typing.Protocol` for polymorphism points
- The `Game` object is a thin shell over an immutable `World` + a `Random` instance

For implementation, **use `@nw-software-crafter`**: it handles the OOP seam and the pure-function core alike. *Why:* `@nw-functional-software-crafter` targets FP-first stacks, and this project's public surface is OOP.

The paradigm decision is recorded in `docs/feature/wumpus/feature-delta.md` § `## Wave: DESIGN / [REF] ADRs` § ADR-001.

## Mutation Testing Strategy

Mutation testing is a **local developer practice** during slice completion; CI does not run it. Run it locally to find weak spots in the test suite; surviving mutants either get killing tests in the same slice or a documented exemption in `MUTATION_EXEMPTIONS.md`. Kill-rate target: **≥ 80 %** on the slice's modified files (excluding equivalent mutants).

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

This replaces the standard nWave per-wave layout (`docs/feature/<feature>/discuss/*.md`, `docs/feature/<feature>/design/*.md`, etc.). Pointer files at the canonical SSOT paths (`docs/product/architecture/brief.md`, `docs/product/journeys/*.md`, `docs/product/kpi-contracts.yaml`) point back to the inline content.

When invoked for a wave, agents:
1. Read the existing `## Wave: <PRIOR> / [REF] ...` sections from `feature-delta.md`
2. Append new `## Wave: <CURRENT> / [REF] ...` sections after the last existing section
3. Write prose wave artifacts only into `feature-delta.md`. Per-wave folders hold machine state only: `deliver/roadmap.json`, `deliver/execution-log.json`, and `deliver/mutation/`.
4. Leave `docs/product/` to the orchestrator; edit it only when the user directs it.

*Why:* one reviewable file per feature keeps every decision in one place. The earlier `wumpus-classic` feature used the per-wave layout; its `discuss/` folder now sits in `docs/feature/.archive/wumpus-classic-2026-05-20/`.

*Enforced* by `.claude/hooks/docs_guard.py` (see § Guards): it denies `.md`/`.yaml` writes under per-wave folders and asks before any write under `docs/product/`.

## Research summaries

`docs/research-summaries/<slug>/` holds **research summaries** — the repo's term for an opinionated, house-style distillation of one external paper or article. A research summary is *not* a neutral abstract. It (a) extracts the load-bearing ideas in the project's voice, (b) redraws the source's key diagrams in the harebrain visual language, and (c) maps the work back onto the **harebrain hypothesis** (`harebrain = fast LLM brain × structured game-AI cage`). Use `docs/research-summaries/llm-modulo/` as the canonical template.

**When the user says "make me a research summary on X":** resolve X to its source, create `docs/research-summaries/<slug>/`, and follow the template below. If X is downloadable (an arXiv paper, a public PDF), fetch it into the folder — for arXiv, `https://arxiv.org/pdf/<id>` → save as a descriptive filename. Read the full source before writing. Work backward from `summary-done`; a target is done only when its prerequisites are:

```
summary-done:        readme-row sources-footer   # README.md research-summaries table gets a row
sources-footer:      harebrain-mapping            # full citation; link the local PDF when one exists
harebrain-mapping:   body-and-figures             # § Where this sits + two-column mapping figure
body-and-figures:    source-read-in-full          # every SVG rendered and checked in light AND dark mode
source-read-in-full: source-fetched               # arXiv: https://arxiv.org/pdf/<id>
```

Directory shape:

- `<slug>/<slug>.md` — the summary
- `<slug>/images/glyph.svg` — masthead glyph
- `<slug>/images/fig-0N-*.svg` — original figures redrawn for the page
- `<slug>/<descriptive-name>-<arxiv-id>.pdf` — the source PDF when one exists
- A multi-part series gets one parent folder: `<series>/<series>.md` (overview) plus one `<series>/<part-slug>/` per part (see `synthetic-scars/`).

`.md` structure (copy the section order of `llm-modulo/llm-modulo.md`):

1. masthead line: `![alt](images/glyph.svg)`
2. `# <Title>, *<gerund>*` — the gerund is the house tic (*distilled*, *redrawn*, *graded*, *audited*, *composed*, *staged*)
3. an italic subtitle line naming the source and its tie to harebrain
4. a `---` rule
5. opinionated body — prose, tables, `> **callout.**` blockquotes, and the redrawn figures inline with italic captions
6. a `## Where this sits in the harebrain hypothesis` section anchored by a two-column mapping figure (source constructs ↔ harebrain primitives)
7. a `**Sources.**` footer: full citation, arXiv id, and a link to the local PDF

**SVG conventions** (theme-adaptive — see the [[harebrain-md-layout]] memory and any existing `glyph.svg`):

- Class-based `currentColor` + an `@media (prefers-color-scheme: dark)` block, so every color has a dark-mode value. *Why:* Phil reads markdown in dark mode locally.
- Reference SVGs as `<img>` via markdown `![]()`. GitHub's sanitizer strips inline `<svg>`; loading via `<img>` preserves the embedded `<style>`/media query.
- Palette tokens (light / dark): ink `#1a1810`/`#ede2c4`, muted `#5d553f`/`#a89c7d`, **oxblood** `#8b1f2c`/`#e09098` (the external/source side), **blueprint** `#1f4f7a`/`#88c0e8` (the harebrain side), sage `#4f6b3f`/`#b1c98c`, plus `*-tint` fills at ~6–10 % alpha.
- Fonts: `Fraunces, serif` for headings/labels (often `font-style="italic"`), `JetBrains Mono`/`ui-monospace` for code-ish labels.
- *Enforced* by the pre-commit hook `svg-theme-check` (see § Guards): it rejects doc SVGs without a dark-mode block and markdown with inline `<svg>`.

## Repository layout

- `python/packages/` — uv workspace packages (wumpus engine + sibling packages)
- `wumpus/` — wumpus-feature scratch space (BASIC source, experiments, design notes)
- `docs/feature/<feature-id>/feature-delta.md` — canonical SSOT for each feature's wave artifacts
- `docs/product/` — product-level SSOT (architecture pointer, journeys, jobs, KPI contracts)
- `docs/research/` — evidence-backed research documents
- `docs/research-summaries/<slug>/` — house-style distillations of external papers (see § Research summaries)
- `.claude/hooks/` — Claude Code hook scripts (see § Guards)
- `scripts/` — repo checks run by pre-commit
- `.github/workflows/` — CI workflows (materialized from `## Wave: DEVOPS / [REF] CI Workflows` specs in feature-delta files)

## Active features

| Feature | SSOT |
|---|---|
| `wumpus` engine | `docs/feature/wumpus/feature-delta.md` |

Derive a feature's status from its artifacts; this table lists features, not their progress.
- Current wave and deferred work: the last `## Wave:` sections of the SSOT.
- Mutation testing: `docs/feature/<feature>/deliver/mutation/mutation-report.md`.
- Finalized: the feature has moved to `docs/evolution/`.

## Guards

Rules a machine can check live in code, not in this file. Each guard ships with tests that replay the bad input it exists to reject.

| Guard | Enforces | Tests |
|---|---|---|
| `.claude/hooks/docs_guard.py` (PreToolUse on Write/Edit/NotebookEdit, wired in `.claude/settings.json`) | § Feature documentation convention, items 3–4 | `python3 -m unittest discover -s .claude/hooks` |
| `scripts/check_svg_theme.py` (pre-commit `svg-theme-check`) | § Research summaries, SVG conventions | `python3 -m unittest discover -s scripts` |

Both test suites also run as the pre-commit hook `guard-tests`. A guard that blocks a legitimate write needs a new allowlist entry and a test, not a workaround.

## When an agent repeats a mistake

Record it as a scar: **Wound** (what went wrong, with the commit or file as evidence), **Trap** (the tempting shortcut), **Reflex** (the affirmative rule). Put it in the relevant section above, or in a feedback memory if it is about working style. Once a guard enforces the reflex, shrink the prose to a pointer to that guard.
