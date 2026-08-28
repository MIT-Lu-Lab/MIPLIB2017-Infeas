"""Load the versioned release manifest shared by release-facing commands.

The JSON Schema is the structural contract.  Python adds only constraints that
Draft 2020-12 cannot express: artifact names are unique and ``sidecar_schema``
names an artifact whose role is ``schema``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator  # pyright: ignore[reportMissingModuleSource]
from jsonschema.exceptions import (  # pyright: ignore[reportMissingModuleSource]
    SchemaError,
    ValidationError,
)

from website.jsonio import read_json

MANIFEST_VERSION = "1.0.0"
MANIFEST_ASSET_NAME = "release-manifest.json"
VERIFICATION_ASSET_NAME = "verify-published.csv"

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _ROOT / "schema" / "release-manifest" / MANIFEST_VERSION / "manifest.schema.json"


@dataclass(frozen=True)
class ManifestAsset:
    """One payload entry from a validated release manifest."""

    name: str
    role: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Manifest:
    """The release identity and its validated payload inventory."""

    tag: str
    source_commit: str
    artifacts: tuple[ManifestAsset, ...]


@cache
def _validator() -> Draft202012Validator:
    schema = read_json(_SCHEMA_PATH, error_type=ValueError)
    if not isinstance(schema, Mapping):
        raise ValueError(f"{_SCHEMA_PATH}: release manifest schema must be an object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f"{_SCHEMA_PATH}: invalid release manifest schema: {exc.message}") from exc
    return Draft202012Validator(schema)


def _location(error: ValidationError) -> str:
    location = "manifest"
    for part in error.absolute_path:
        location += f"[{part}]" if isinstance(part, int) else f".{part}"
    return location


def parse_manifest(document: object) -> Manifest:
    """Validate and decode one manifest using its published JSON Schema."""
    try:
        _validator().validate(document)
    except ValidationError as exc:
        raise ValueError(f"{_location(exc)}: {exc.message}") from None

    root = cast(dict[str, Any], document)
    raw_release = cast(dict[str, Any], root["release"])
    raw_artifacts = cast(list[dict[str, Any]], root["artifacts"])

    artifacts = tuple(
        ManifestAsset(
            name=cast(str, item["name"]),
            role=cast(str, item["role"]),
            size=int(item["bytes"]),
            sha256=cast(str, item["sha256"]),
        )
        for item in raw_artifacts
    )
    by_name: dict[str, ManifestAsset] = {}
    for artifact in artifacts:
        if artifact.name in by_name:
            raise ValueError(f"manifest names {artifact.name!r} more than once")
        by_name[artifact.name] = artifact

    schema_asset = cast(str, root["sidecar_schema"])
    bound_schema = by_name.get(schema_asset)
    if bound_schema is None:
        raise ValueError("sidecar_schema is not present in artifacts")
    if bound_schema.role != "schema":
        raise ValueError("sidecar_schema must name an artifact with the schema role")

    return Manifest(
        tag=cast(str, raw_release["tag"]),
        source_commit=cast(str, raw_release["source_commit"]),
        artifacts=artifacts,
    )


def load_manifest(path: Path) -> Manifest:
    """Read, validate and decode a manifest from disk."""
    return parse_manifest(read_json(path, error_type=ValueError))
