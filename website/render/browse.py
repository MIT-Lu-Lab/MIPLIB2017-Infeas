"""One subset's browse page: the facet rail and the sortable table."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .. import content
from ..domain import SUBSET_SPECS, Sample, Subset
from ..urls import rel
from .facets import facets_for, memberships_for, row_values
from .shell import page


@dataclass(frozen=True)
class Column:
    """One displayed field and its human-readable formatter."""

    label: str
    field: str
    formatter: Callable[[int], str] = content.fmt_int


_COMMON_COLUMNS = (
    Column("Variables", "n_vars"),
    Column("Constraints", "n_cons"),
    Column("Nonzeros", "nnz"),
)
_FILE_COLUMN = Column("File", "file_bytes", content.fmt_bytes)

COLUMNS: dict[Subset, tuple[Column, ...]] = {
    "primal": (
        *_COMMON_COLUMNS,
        Column("Depth", "depth"),
        Column("Bounds tightened", "bound_changes"),
        _FILE_COLUMN,
    ),
    "dual": (
        *_COMMON_COLUMNS,
        Column("Bounds dropped", "bounds_dropped"),
        Column("Rows dropped", "rows_dropped"),
        _FILE_COLUMN,
    ),
}


def page_rel(subset: Subset) -> str:
    """Where this subset's browse page goes, and what its links resolve from."""

    return f"{SUBSET_SPECS[subset].slug}/index.html"


def _instances(count: int) -> str:
    return f"{content.fmt_int(count)} {'instance' if count == 1 else 'instances'}"


def _tabs(subset: Subset, samples: Sequence[Sample]) -> tuple[dict[str, object], ...]:
    """Both halves of the collection, primal first.

    The order is the order of the two-colour hairline under the top bar, so the
    switch sits where the site already says each half lives. The half being
    rendered has no href: it is the page's own heading, and a link to where you
    already are is one more thing to read past.
    """

    return tuple(
        {
            "label": spec.label,
            "tone": spec.tone,
            "count": _instances(sum(1 for sample in samples if sample.subset == other)),
            "href": None if other == subset else rel(page_rel(subset), f"{spec.slug}/"),
        }
        for other, spec in SUBSET_SPECS.items()
    )


def render_browse(
    subset: Subset,
    samples: Sequence[Sample],
    release_base_url: str | None = None,
    site_url: str | None = None,
) -> str:
    """Render one subset's facet rail and sortable table."""

    info = SUBSET_SPECS[subset]
    rows = [sample for sample in samples if sample.subset == subset]
    values = [row_values(sample) for sample in rows]
    columns = COLUMNS[subset]
    natural = sum(sample.dual.natural_unbounded for sample in rows) if subset == "dual" else 0
    facets = facets_for(subset, values)
    memberships = [memberships_for(facets, value) for value in values]
    client_fields = ("instance", *(column.field for column in columns))
    count = _instances(len(rows))
    archive_label = (
        f"{count}, {content.fmt_bytes(sum(sample.total_bytes for sample in rows))} unpacked"
    )

    return page(
        "browse.html",
        f"{info.label} instances",
        active=subset,
        page_rel=page_rel(subset),
        description=content.subset_description(subset, len(rows), natural),
        site_url=site_url,
        info=info,
        tabs=_tabs(subset, samples),
        blurb=content.subset_summary(subset, len(rows), natural),
        table_id=f"{info.slug}-table-caption",
        total_label=count,
        archive_label=archive_label,
        archive_href=f"{release_base_url}/{info.slug}.zip" if release_base_url else None,
        columns=columns,
        facet_groups=tuple(
            {
                "label": facet.label,
                "param": facet.param,
                "buckets": tuple(
                    {
                        "key": facet.key(bucket),
                        "label": bucket.label,
                        "count": sum(facet.key(bucket) in row for row in memberships),
                    }
                    for bucket in facet.buckets
                ),
            }
            for facet in facets
        ),
        table_rows=tuple(
            {
                "name": value["instance"],
                "cells": tuple(column.formatter(value[column.field]) for column in columns),
                "download_label": f"Download {value['instance']} as gzipped MPS",
                "download_href": (
                    f"{release_base_url}/{sample.stem}.mps.gz" if release_base_url else None
                ),
            }
            for sample, value in zip(rows, values, strict=True)
        ),
        browse_data={
            "rows": [
                {
                    "values": {field: value[field] for field in client_fields},
                    "matches": matches,
                }
                for value, matches in zip(values, memberships, strict=True)
            ]
        },
    )
