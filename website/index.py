"""Strict adapters between JSON-shaped input and trusted domain objects."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Literal, cast

from .domain import (
    BoundDrop,
    DomainError,
    Drop,
    DualProvenance,
    PrimalProvenance,
    RowDrop,
    Sample,
    Subset,
    validate_drop_indices,
)
from .jsonio import read_json

INDEX_VERSION = 2


class SiteIndexError(ValueError):
    """A site index or optional metadata cache is malformed."""


def _mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SiteIndexError(f"{context} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, context: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SiteIndexError(f"{context} must be an array")
    return cast(Sequence[object], value)


def _exact_keys(obj: Mapping[str, object], expected: set[str], context: str) -> None:
    missing = expected - set(obj)
    if missing:
        raise SiteIndexError(f"{context} is missing fields: {', '.join(sorted(missing))}")
    unexpected = set(obj) - expected
    if unexpected:
        raise SiteIndexError(f"{context} has unknown fields: {', '.join(sorted(unexpected))}")


# An instance name is also a directory the site publishes it under, so a name
# with a separator in it would quietly nest a page instead of being rejected.
# Other path portability rules are enforced for every generated file by output.py.
_INSTANCE_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _instance_name(value: object, context: str) -> str:
    name = _string(value, context)
    if not _INSTANCE_RE.fullmatch(name):
        raise SiteIndexError(f"{context} cannot be a directory name: {name!r}")
    return name


def _sha256(value: object, context: str) -> str | None:
    if value is None:
        return None
    digest = _string(value, context)
    if not _SHA256_RE.fullmatch(digest):
        raise SiteIndexError(f"{context} must be 64 lowercase hex digits, got {digest!r}")
    return digest


def _string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise SiteIndexError(f"{context} must be a string, got {value!r}")
    return value


def _optional_string(value: object, context: str) -> str | None:
    if value is None:
        return None
    return _string(value, context)


def _integer(value: object, context: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise SiteIndexError(f"{context} must be an integer, got {value!r}")
    result = cast(int, value)
    if result < minimum:
        raise SiteIndexError(f"{context} must be at least {minimum}, got {result}")
    return result


def _boolean(value: object, context: str) -> bool:
    if type(value) is not bool:
        raise SiteIndexError(f"{context} must be a boolean, got {value!r}")
    return cast(bool, value)


def _number(value: object, context: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SiteIndexError(f"{context} must be a number, got {value!r}")
    if not math.isfinite(value):
        raise SiteIndexError(f"{context} must be finite, got {value!r}")
    return value


def _enum(value: object, choices: tuple[str, ...], context: str) -> str:
    if not isinstance(value, str) or value not in choices:
        rendered = ", ".join(repr(choice) for choice in choices)
        raise SiteIndexError(f"{context} must be one of {rendered}, got {value!r}")
    return value


def _strings(value: object, context: str) -> tuple[str, ...]:
    values = _sequence(value, context)
    result = []
    for position, item in enumerate(values):
        result.append(_string(item, f"{context}[{position}]"))
    return tuple(result)


def _drop(value: object, context: str) -> Drop:
    obj = _mapping(value, context)
    if "kind" not in obj:
        raise SiteIndexError(f"{context} is missing field: kind")
    kind = _enum(obj["kind"], ("bound", "row"), f"{context}.kind")
    required = {"kind", "var", "side"} if kind == "bound" else {"kind", "row"}
    _exact_keys(obj, required | ({"name"} if "name" in obj else set()), context)
    if kind == "bound":
        drop: BoundDrop = {
            "kind": "bound",
            "var": _integer(obj["var"], f"{context}.var"),
            "side": cast(
                Literal["lb", "ub"],
                _enum(obj["side"], ("lb", "ub"), f"{context}.side"),
            ),
        }
        if "name" in obj:
            drop["name"] = _string(obj["name"], f"{context}.name")
        return drop

    drop_row: RowDrop = {
        "kind": "row",
        "row": _integer(obj["row"], f"{context}.row"),
    }
    if "name" in obj:
        drop_row["name"] = _string(obj["name"], f"{context}.name")
    return drop_row


def to_record(sample: Sample) -> dict[str, object]:
    """Serialise the dataset-derived half of a sample for the site index."""

    provenance = sample.provenance
    if isinstance(provenance, PrimalProvenance):
        provenance_record: dict[str, object] = {
            "depth": provenance.depth,
            "bound_changes": provenance.bound_changes,
            "branch_sense": provenance.branch_sense,
            "branch_value": provenance.branch_value,
            "branch_var": provenance.branch_var,
            "branch_var_name": provenance.branch_var_name,
            "path_head": provenance.path_head,
        }
    else:
        provenance_record = {
            "bounds_dropped": provenance.bounds_dropped,
            "rows_dropped": provenance.rows_dropped,
            "natural_unbounded": provenance.natural_unbounded,
            "rounds": provenance.rounds,
            "drops_head": provenance.drops_head,
        }
    return {
        "instance": sample.instance,
        "n_vars": sample.n_vars,
        "n_cons": sample.n_cons,
        "nnz": sample.nnz,
        "file_bytes": sample.file_bytes,
        "meta_bytes": sample.meta_bytes,
        "sha256": sample.sha256,
        "subset": sample.subset,
        "provenance": provenance_record,
    }


def from_record(record: object) -> Sample:
    """Validate and rebuild one version-2 site-index record."""

    obj = _mapping(record, "record")
    _exact_keys(
        obj,
        {
            "instance",
            "n_vars",
            "n_cons",
            "nnz",
            "file_bytes",
            "meta_bytes",
            "sha256",
            "subset",
            "provenance",
        },
        "record",
    )
    instance = _instance_name(obj["instance"], "record.instance")
    context = f"record {instance!r}"
    subset = cast(
        Subset,
        _enum(obj["subset"], ("primal", "dual"), f"{context}.subset"),
    )

    where = f"{context}.provenance"
    provenance_obj = _mapping(obj["provenance"], where)
    try:
        if subset == "primal":
            _exact_keys(
                provenance_obj,
                {
                    "depth",
                    "bound_changes",
                    "branch_sense",
                    "branch_value",
                    "branch_var",
                    "branch_var_name",
                    "path_head",
                },
                where,
            )
            provenance: PrimalProvenance | DualProvenance = PrimalProvenance(
                depth=_integer(provenance_obj["depth"], f"{where}.depth"),
                bound_changes=_integer(provenance_obj["bound_changes"], f"{where}.bound_changes"),
                branch_sense=cast(
                    Literal[">=", "<="],
                    _enum(
                        provenance_obj["branch_sense"],
                        (">=", "<="),
                        f"{where}.branch_sense",
                    ),
                ),
                branch_value=float(
                    _number(provenance_obj["branch_value"], f"{where}.branch_value")
                ),
                branch_var=_integer(provenance_obj["branch_var"], f"{where}.branch_var"),
                branch_var_name=_optional_string(
                    provenance_obj["branch_var_name"], f"{where}.branch_var_name"
                ),
                path_head=_strings(provenance_obj["path_head"], f"{where}.path_head"),
            )
        else:
            _exact_keys(
                provenance_obj,
                {"bounds_dropped", "rows_dropped", "natural_unbounded", "rounds", "drops_head"},
                where,
            )
            drops = tuple(
                _drop(drop, f"{where}.drops_head[{position}]")
                for position, drop in enumerate(
                    _sequence(provenance_obj["drops_head"], f"{where}.drops_head")
                )
            )
            provenance = DualProvenance(
                bounds_dropped=_integer(
                    provenance_obj["bounds_dropped"], f"{where}.bounds_dropped"
                ),
                rows_dropped=_integer(provenance_obj["rows_dropped"], f"{where}.rows_dropped"),
                natural_unbounded=_boolean(
                    provenance_obj["natural_unbounded"], f"{where}.natural_unbounded"
                ),
                rounds=(
                    None
                    if provenance_obj["rounds"] is None
                    else _integer(provenance_obj["rounds"], f"{where}.rounds")
                ),
                drops_head=drops,
            )

        sample = Sample(
            instance=instance,
            n_vars=_integer(obj["n_vars"], f"{context}.n_vars", minimum=1),
            n_cons=_integer(obj["n_cons"], f"{context}.n_cons"),
            nnz=_integer(obj["nnz"], f"{context}.nnz"),
            file_bytes=_integer(obj["file_bytes"], f"{context}.file_bytes", minimum=1),
            meta_bytes=_integer(obj["meta_bytes"], f"{context}.meta_bytes"),
            sha256=_sha256(obj["sha256"], f"{context}.sha256"),
            provenance=provenance,
        )
        if isinstance(provenance, DualProvenance):
            validate_drop_indices(
                provenance.drops_head,
                n_vars=sample.n_vars,
                source_rows=sample.n_cons + provenance.rows_dropped,
            )
    except DomainError as exc:
        raise SiteIndexError(f"{context}: {exc}") from exc
    return sample


def with_source_metadata(sample: Sample, miplib: object | None) -> Sample:
    """Validate and attach one optional MIPLIB metadata entry."""

    if miplib is None:
        return sample
    values = _mapping(miplib, f"MIPLIB metadata for {sample.instance!r}")
    context = f"MIPLIB metadata for {sample.instance!r}"
    raw_tags = values.get("tags", ())
    tags = _strings(raw_tags, f"{context}.tags")
    return replace(
        sample,
        submitter=_optional_string(values.get("submitter"), f"{context}.submitter"),
        tags=tags,
        source_description=_optional_string(values.get("description"), f"{context}.description"),
        source_group=_optional_string(values.get("group"), f"{context}.group"),
        imported_from=_optional_string(values.get("imported_from"), f"{context}.imported_from"),
    )


def with_search_metadata(sample: Sample, entry: object | None) -> Sample:
    """Attach the node count of the run that produced a primal file."""

    if entry is None:
        return sample
    context = f"search metadata for {sample.instance!r}"
    values = _mapping(entry, context)
    return replace(sample, search_nodes=_integer(values["nodes"], f"{context}.nodes", minimum=1))


def load_collection(
    index_path: Path | str,
    miplib_path: Path | str | None = None,
    search_path: Path | str | None = None,
) -> tuple[Sample, ...]:
    """Load, validate, de-duplicate, and deterministically order a site index."""

    path = Path(index_path)
    if not path.exists():
        raise SiteIndexError(
            f"{index_path}: no site index. python -m scripts.build_site_index writes one "
            "from a checkout of the published dataset."
        )
    doc = _mapping(read_json(path, error_type=SiteIndexError), str(path))
    _exact_keys(doc, {"version", "records"}, str(path))
    version = _integer(doc["version"], f"{path}.version")
    if version != INDEX_VERSION:
        raise SiteIndexError(
            f"{index_path}: index version {version!r}, expected {INDEX_VERSION}. "
            "Regenerate it with python -m scripts.build_site_index."
        )

    raw_records = _sequence(doc["records"], f"{path}.records")
    if not raw_records:
        raise SiteIndexError(f"{index_path}: holds no records")
    miplib: Mapping[str, object] = {}
    if miplib_path is not None:
        metadata_path = Path(miplib_path)
        if not metadata_path.exists():
            raise SiteIndexError(f"{metadata_path}: metadata cache does not exist")
        miplib = _mapping(read_json(metadata_path, error_type=SiteIndexError), str(metadata_path))
    search: Mapping[str, object] = {}
    if search_path is not None:
        search_file = Path(search_path)
        if not search_file.exists():
            raise SiteIndexError(f"{search_file}: search metadata does not exist")
        search = _mapping(read_json(search_file, error_type=SiteIndexError), str(search_file))
    samples: list[Sample] = []
    keys: set[tuple[Subset, str]] = set()
    page_paths: set[str] = set()
    for position, raw_record in enumerate(raw_records):
        try:
            sample = from_record(raw_record)
            source = miplib.get(sample.instance)
            sample = with_source_metadata(sample, source)
            if sample.subset == "primal":
                sample = with_search_metadata(sample, search.get(sample.instance))
            key = (sample.subset, sample.instance)
            if key in keys:
                raise SiteIndexError(f"duplicate sample {sample.subset}/{sample.instance}")
            folded_path = sample.page_path.casefold()
            if folded_path in page_paths:
                raise SiteIndexError(f"case-insensitive page-path collision at {sample.page_path}")
        except SiteIndexError as exc:
            raise SiteIndexError(f"{path}.records[{position}]: {exc}") from exc
        keys.add(key)
        page_paths.add(folded_path)
        samples.append(sample)

    samples.sort(key=lambda sample: (sample.subset, sample.instance))
    return tuple(samples)
