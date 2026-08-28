"""Strict JSON input shared by the repository's file contracts."""

from __future__ import annotations

import json
from pathlib import Path


class JsonError(ValueError):
    """A JSON document cannot be read without extensions or duplicate keys."""


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError(f"non-standard numeric constant {value}")


def read_json(path: Path | str, *, error_type: type[ValueError] = JsonError) -> object:
    """Read strict UTF-8 JSON, reporting failures through ``error_type``."""

    source = Path(path)
    try:
        return json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_object,
            parse_constant=_constant,
        )
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise error_type(f"{source}: invalid JSON: {exc}") from exc
