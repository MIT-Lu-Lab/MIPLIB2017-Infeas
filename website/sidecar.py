"""Producer-only adapter from published sidecars to site domain objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from functools import cache
from pathlib import Path
from typing import Any, Literal, cast

from . import ROOT
from .domain import (
    HEAD_LIMIT,
    BoundDrop,
    DomainError,
    Drop,
    DualProvenance,
    PrimalProvenance,
    RowDrop,
    Sample,
    subset_for_kind,
    validate_drop_indices,
)
from .jsonio import read_json

_SCHEMA = ROOT / "schema" / "meta.schema.json"


class SidecarError(ValueError):
    """A sidecar cannot be projected into the site index."""


def _integer(value: object, context: str, *, minimum: int = 0) -> int:
    # JSON Schema treats 1.0 as an integer; the index deliberately does not.
    if type(value) is not int:
        raise SidecarError(f"{context} must be an integer, got {value!r}")
    result = cast(int, value)
    if result < minimum:
        raise SidecarError(f"{context} must be at least {minimum}, got {result}")
    return result


@cache
def _validator() -> Any:
    import jsonschema

    schema = read_json(_SCHEMA, error_type=SidecarError)
    if not isinstance(schema, Mapping):
        raise SidecarError("sidecar schema must be an object")
    return jsonschema.Draft202012Validator(schema)


def _pointer(path: Iterable[object]) -> str:
    return "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in path)


def _drop(value: Mapping[str, Any], position: int) -> Drop:
    name = value.get("name")
    if value["kind"] == "bound":
        drop: BoundDrop = {
            "kind": "bound",
            "var": _integer(value["var"], f"sidecar.drops[{position}].var"),
            "side": cast(Literal["lb", "ub"], value["side"]),
        }
        if name is not None:
            drop["name"] = name
        return drop

    drop_row: RowDrop = {
        "kind": "row",
        "row": _integer(value["row"], f"sidecar.drops[{position}].row"),
    }
    if name is not None:
        drop_row["name"] = name
    return drop_row


def sample_from_meta(meta: object, file_bytes: int, meta_bytes: int) -> Sample:
    """Validate and project one miner sidecar into the site's domain model."""

    error = next(_validator().iter_errors(meta), None)
    if error is not None:
        raise SidecarError(f"sidecar{_pointer(error.absolute_path)}: {error.message}")

    # The schema establishes the shape; Any records that fact for the checker.
    doc = cast("dict[str, Any]", meta)
    context = f"sidecar {doc['instance']!r}"
    drops: tuple[Drop, ...] = ()
    try:
        if subset_for_kind(doc["sample_kind"]) == "primal":
            entries = tuple(doc["path_entries"])
            named = tuple(doc.get("path_head_named") or ())
            provenance: PrimalProvenance | DualProvenance = PrimalProvenance(
                depth=_integer(doc["depth"], "sidecar.depth"),
                bound_changes=len(entries),
                branch_sense=cast(Literal[">=", "<="], doc["branch_sense"]),
                branch_value=float(doc["branch_value"]),
                branch_var=_integer(doc["branch_var"], "sidecar.branch_var"),
                branch_var_name=doc.get("branch_var_name"),
                path_head=cast(tuple[str, ...], named or entries[:HEAD_LIMIT]),
            )
        else:
            drops = tuple(_drop(drop, position) for position, drop in enumerate(doc["drops"]))
            bounds_dropped = sum(drop["kind"] == "bound" for drop in drops)
            if "n_dropped" in doc and doc["n_dropped"] != len(drops):
                raise SidecarError(
                    f"{context}.n_dropped is {doc['n_dropped']}, but drops has {len(drops)} entries"
                )
            provenance = DualProvenance(
                bounds_dropped=bounds_dropped,
                rows_dropped=len(drops) - bounds_dropped,
                natural_unbounded=doc["natural_unbounded"],
                drops_head=drops[:HEAD_LIMIT],
                # optional in the published schema, so absent stays absent
                rounds=doc.get("n_rounds"),
            )
        sample = Sample(
            instance=doc["instance"],
            n_vars=_integer(doc["n_vars"], "sidecar.n_vars", minimum=1),
            n_cons=_integer(doc["n_cons"], "sidecar.n_cons"),
            nnz=_integer(doc["nnz"], "sidecar.nnz"),
            file_bytes=_integer(file_bytes, "file_bytes", minimum=1),
            meta_bytes=_integer(meta_bytes, "meta_bytes"),
            sha256=doc.get("sha256"),
            provenance=provenance,
        )
        if isinstance(provenance, DualProvenance):
            validate_drop_indices(
                drops,
                n_vars=sample.n_vars,
                source_rows=sample.n_cons + provenance.rows_dropped,
            )
    except DomainError as exc:
        raise SidecarError(f"{context}: {exc}") from exc
    return sample


def load_sidecar(path: Path, *, file_bytes: int) -> Sample:
    """Strictly read and project one sidecar, measuring its own byte length."""

    document = read_json(path, error_type=SidecarError)
    return sample_from_meta(document, file_bytes, path.stat().st_size)
