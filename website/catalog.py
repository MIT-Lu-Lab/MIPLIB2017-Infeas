"""Serialize the public machine-readable catalogue."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence

from . import content
from .domain import SUBSET_SPECS, CollectionTotals, Sample, Subset, SubsetSpec

FORMAT_VERSION = 1

_INDEX_HEAD = ("instance", "n_vars", "n_cons", "nnz")
_INDEX_TAIL = ("file_bytes", "sha256", "mps_filename")
_INDEX_COLUMNS: dict[Subset, tuple[str, ...]] = {
    "primal": (*_INDEX_HEAD, "depth", "bound_changes", *_INDEX_TAIL),
    "dual": (*_INDEX_HEAD, "bounds_dropped", "rows_dropped", *_INDEX_TAIL),
}


def subset_rows(subset: Subset, samples: Sequence[Sample]) -> tuple[dict[str, object], ...]:
    """Project one subset into the rows shared by its JSON and CSV indexes."""

    rows = []
    for sample in samples:
        if sample.subset != subset:
            continue
        row: dict[str, object] = {
            "instance": sample.instance,
            "n_vars": sample.n_vars,
            "n_cons": sample.n_cons,
            "nnz": sample.nnz,
        }
        if subset == "primal":
            row.update(
                depth=sample.primal.depth,
                bound_changes=sample.primal.bound_changes,
            )
        else:
            row.update(
                bounds_dropped=sample.dual.bounds_dropped,
                rows_dropped=sample.dual.rows_dropped,
            )
        row.update(
            file_bytes=sample.file_bytes,
            sha256=sample.sha256,
            mps_filename=sample.stem + ".mps.gz",
        )
        rows.append(row)
    return tuple(rows)


def csv_index(subset: Subset, rows: Sequence[dict[str, object]]) -> bytes:
    """Encode catalogue rows in the published column order."""

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    columns = _INDEX_COLUMNS[subset]
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row[name] for name in columns)
    return buffer.getvalue().encode("utf-8")


def _json_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def subset_index(
    subset: Subset,
    info: SubsetSpec,
    rows: Sequence[dict[str, object]],
    release_base_url: str | None,
) -> bytes:
    """Encode one subset's public JSON index."""

    document: dict[str, object] = {
        "format_version": FORMAT_VERSION,
        "subset": subset,
        "label": info.label,
    }
    if release_base_url:
        document["release_base_url"] = release_base_url + "/"
    document["count"] = len(rows)
    document["instances"] = rows
    return _json_bytes(document)


def collection_index(
    totals: CollectionTotals,
    site_url: str | None,
    release_base_url: str | None,
) -> bytes:
    """Encode the top-level public catalogue index."""

    document: dict[str, object] = {
        "format_version": FORMAT_VERSION,
        "name": content.NAME,
        "description": content.collection_summary(totals),
    }
    if site_url:
        document["url"] = site_url
    if release_base_url:
        document["release_base_url"] = release_base_url + "/"
    document["instances"] = totals["n_samples"]
    document["subsets"] = [
        {
            "subset": key,
            "label": info.label,
            "count": totals["counts"][key],
            "index": f"{info.slug}.json",
            "csv": f"{info.slug}.csv",
        }
        for key, info in SUBSET_SPECS.items()
    ]
    document["sidecar_schema"] = content.SIDECAR_SCHEMA_PATH
    document["notice"] = "LICENSE.txt"
    return _json_bytes(document)
