"""Schema loader for the wumpus event ledger (R2-S01).

Locates and loads `wumpus/schemas/v<version>.json` from the installed package.
Per ADR-002 (schema evolution policy) each major version ships its own
schema document; downstream replay tools look up the right document via
`load_schema(version)` keyed on the `schema_version` field on every event.

Wheel-shipped JSON: the `schemas/` directory is in-package (under
`wumpus/schemas/`) so `importlib.resources` returns it deterministically
under both source and wheel installs.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any


def load_schema(version: int) -> dict[str, Any]:
    """Return the parsed JSON Schema for the given wumpus event schema version.

    Raises FileNotFoundError if no `v<version>.json` ships in the package.
    """
    package = "wumpus.schemas"
    filename = f"v{version}.json"
    try:
        with resources.files(package).joinpath(filename).open("r", encoding="utf-8") as fh:
            return json.load(fh)  # type: ignore[no-any-return]
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise FileNotFoundError(
            f"wumpus schema v{version} not found in package 'wumpus.schemas'. "
            f"Expected file: {filename}."
        ) from exc


__all__ = ["load_schema"]
