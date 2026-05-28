# Mutation testing exemptions

Surviving mutants from cosmic-ray runs that are explicitly accepted as **not
worth killing tests for** — either because they're equivalent mutants (no
runtime behavior to distinguish), or because the cost of writing a killing
test outweighs the value. Each entry must justify *why*.

This file is the audit trail for what we chose not to chase. The default is to
**write a killing test**, not exempt. Use this file sparingly.

Format: one entry per accepted survivor or survivor class, with the cosmic-ray
operator + location + reason.

---

## Equivalent mutants on type annotations (cosmic-ray default operators)

Cosmic-ray's `BitOr_*` replacement operators (`|` → `+`, `-`, `*`, `/`, `//`,
`%`, `**`, `>>`, `<<`, `&`, `^`) target the `|` operator generally — including
in `int | None`-style **type-annotation unions** (PEP 604). Python evaluates
these annotations at runtime only for typing-introspection purposes; they have
no observable effect on the program's behavior, so no test can ever kill them.

These are textbook **equivalent mutants**. Accepted as exempted as a class.

Affected sites surface wherever the engine uses `X | None`-style return types
(`room_id`, etc.). The cleaner long-term fix is to configure cosmic-ray's
operator set to skip annotation-context mutations, at which point this exemption
becomes unnecessary.

---

## Per-run survivors (none currently accepted)

Per-run survivors that are *not* type-annotation equivalents should be either
killed with a new test or listed here with a justification. As of the
2026-05-28 mystery.py baseline (`docs/feature/wumpus/deliver/mutation/mutation-report.md`)
the genuine survivors in `MysterySurface.terminal_lines` are **not exempted** —
they are tracked as a real test gap (Mystery terminal-rendering path is not
exercised by any test) and will be killed by adding a forced-win + forced-loss
Mystery scenario in a follow-up.
