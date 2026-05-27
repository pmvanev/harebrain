"""R1-S09 — subprocess-safe CLI entry point.

`wumpus.cli.main` is the driving port harnesses (pexpect / wexpect / oracle
replay tools) wrap. The contract is SC3:

  - Line-buffered stdout (`sys.stdout.reconfigure(line_buffering=True)`)
  - No curses, no SDL, no readline mode that changes stdin handling for
    non-TTY input
  - Prompts MUST be observable at the harness before the engine awaits input

The loop is thin: parse argv, build the Game, attach a RendererSink to
stdout, then loop on `input()` -> `game.step()` until the session terminates
(SessionEnded or alive=False with no pending prompt).

Argument surface (R1-S09 + R2-S01):
  - `--seed INT`            optional; if omitted Game(seed=None) auto-rolls
                            via OS entropy at construction
  - `--ledger PATH`         R2-S01: when set, the CLI attaches a JsonlSink
                            writing schema-validated v1 events to PATH in
                            append mode. The sink is closed on session exit
                            (clean termination OR stdin EOF).
  - `--surface VARIANT`     placeholder until R4-S03; only "yob" accepted at
                            R1-S09 — other values fail fast with a clear error
  - `--yob`                 explicit-default flag; equivalent to no surface
                            override (self-documenting alias)
  - `--cave {yob,toy}`      debug-only; "toy" selects the R0 3-room linear
                            cave used by the pexpect smoke test (production
                            users will never set this; documented as such
                            in --help)

Per SC8 no Yob string literals live here — the only strings in this module
are argparse help text and error messages.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import TextIO

from wumpus import Game
from wumpus.sinks import JsonlSink, RendererSink
from wumpus.surfaces.mystery import MysterySurface
from wumpus.surfaces.yob import YobSurface
from wumpus.types import Surface


def _build_argument_parser() -> argparse.ArgumentParser:
    """Return the R1-S09 CLI argument parser.

    Defaults:
      - --seed defaults to None (Game auto-rolls OS entropy)
      - --ledger defaults to None (placeholder until R2-S01)
      - --surface defaults to "yob"
      - --cave defaults to "yob" (the real dodecahedron)
    """
    parser = argparse.ArgumentParser(
        prog="wumpus",
        description="Hunt the Wumpus — Yob 1973 faithful CLI",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Seed for the engine's RNG. If omitted, Game auto-rolls via OS "
            "entropy at construction."
        ),
    )
    parser.add_argument(
        "--ledger",
        default=None,
        metavar="PATH",
        help=(
            "Path to a JSONL event ledger. When set, every emitted event is "
            "validated against `wumpus/schemas/v1.json` and appended as one "
            "JSON object per line. The file is opened in append mode + "
            "line-buffered; the first emitted event is the first line "
            "(no separate header). Closed cleanly on session exit."
        ),
    )
    parser.add_argument(
        "--surface",
        default="yob",
        metavar="VARIANT",
        help=(
            "Surface variant to render with. 'yob' (default) is the verbatim "
            "Yob 1973 surface; 'mystery' is the obfuscation-gap probe surface "
            "(R4-S05) — scrambled labels, alien glyph strings, identical "
            "internal trajectory."
        ),
    )
    parser.add_argument(
        "--yob",
        action="store_true",
        help="Explicit-default flag; equivalent to --surface yob.",
    )
    parser.add_argument(
        "--cave",
        default="yob",
        choices=("yob", "toy"),
        help=(
            "Cave topology. 'yob' is the canonical 20-room dodecahedron "
            "(default). 'toy' is a 3-room linear test/debug cave used by "
            "the R1-S09 pexpect smoke test — production users should never "
            "set this."
        ),
    )
    return parser


_SURFACE_BY_NAME: dict[str, type[Surface]] = {
    "yob": YobSurface,
    "mystery": MysterySurface,
}


def _resolve_surface(parser: argparse.ArgumentParser, surface: str) -> Surface:
    """Resolve the `--surface` name to a Surface instance.

    R4-S05: 'yob' (default) and 'mystery' are wired. Any other value fails fast
    with a clear error (SC8 — the engine never sees an unvalidated surface)."""
    surface_class = _SURFACE_BY_NAME.get(surface)
    if surface_class is None:
        parser.error(
            f"--surface={surface!r} is not supported; "
            f"choose one of {sorted(_SURFACE_BY_NAME)!r}."
        )
    return surface_class()


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Run the wumpus CLI loop to completion.

    `argv`, `stdin`, `stdout` are injectable to support in-process
    acceptance + unit tests (StringIO substitutes). Production callers
    invoke `main()` with no arguments — `argv` defaults to `sys.argv[1:]`
    and the streams default to the real `sys.stdin` / `sys.stdout`.

    Termination conditions (the loop exits on any of):
      - SessionEnded fires (`world.alive=False` AND `pending_prompt is None`)
        — the post-terminal SAME SET-UP=N path
      - stdin reaches EOF (the harness closed the input stream cleanly)

    Per SC3 the loop never calls `input(prompt=...)` with the prompt
    argument — prompts come from rendered events written to stdout by the
    RendererSink. This avoids the readline path that buffers the prompt
    differently for non-TTY stdin.
    """
    if stdout is None:
        stdout = sys.stdout
        # Production path: enable line-buffering on the real stdout so each
        # `print`/`write+"\n"` flushes before the loop blocks on input().
        # In-process tests inject a StringIO which doesn't have reconfigure
        # — the `getattr` defends against the StringIO branch.
        reconfigure = getattr(stdout, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(line_buffering=True)
            except (TypeError, ValueError):
                # Some TextIO subclasses don't accept line_buffering — fall
                # back to per-write flush via the RendererSink's flush call.
                pass
    if stdin is None:
        stdin = sys.stdin

    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    surface = _resolve_surface(parser, args.surface)

    game = Game(
        seed=args.seed if args.seed is not None else 0,
        cave=args.cave,
        surface=surface,
    )
    renderer_sink = RendererSink(stream=stdout, surface=surface)
    game.subscribe(renderer_sink)
    ledger_sink: JsonlSink | None = None
    if args.ledger is not None:
        ledger_sink = JsonlSink(pathlib.Path(args.ledger))
        game.subscribe(ledger_sink)

    try:
        while not _session_terminated(game):
            try:
                line = stdin.readline()
            except EOFError:
                break
            if line == "":
                # readline returns "" only on EOF (a blank input line is "\n").
                break
            action = line.rstrip("\r\n")
            game.step(action)
    finally:
        # SC4: synchronous + ordered emission. Closing the ledger AFTER the
        # loop ensures every event the engine emitted has been written and
        # flushed before the process exits. The renderer sink doesn't need
        # explicit close — it writes to stdout, which the OS owns.
        if ledger_sink is not None:
            ledger_sink.close()


def _session_terminated(game: Game) -> bool:
    """Return True when the engine is in a terminal state with no awaited
    input. Session termination = `alive=False` AND `pending_prompt is None`
    (the SessionEnded post-condition — see `Game._end_session`)."""
    world = game.world_state()
    return (not world.alive) and (world.pending_prompt is None)


__all__ = ["main"]
