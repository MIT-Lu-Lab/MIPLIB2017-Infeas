"""Facet declarations shared by rail counts and client memberships."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..content import NON_LP_TAGS
from ..domain import Sample, Subset

# A tag narrows the table only if enough instances carry it; below this it is a
# checkbox that removes almost everything or almost nothing.
TAG_FACET_MIN = 8


@dataclass(frozen=True)
class Range:
    """A half-open bucket of a numeric field: lo <= value < hi.

    An open end is None. Half-open rather than inclusive so that adjacent
    buckets share one number instead of one number and its successor.
    """

    label: str
    value: str
    lo: int | None = None
    hi: int | None = None

    def holds(self, value: int | float) -> bool:
        return (self.lo is None or value >= self.lo) and (self.hi is None or value < self.hi)


@dataclass(frozen=True)
class Term:
    """One value of a categorical field.

    A field that holds a list, as tags do, is held by any term in the list.
    """

    label: str
    value: str

    def holds(self, value: object) -> bool:
        if isinstance(value, (list, tuple)):
            return self.value in value
        return value == self.value


@dataclass(frozen=True)
class Facet:
    """One group of checkboxes: a label, the row field it reads, its buckets.

    `param` names the facet where a reader can see it, in a row's tokens and in
    the query string, so it is chosen to read well. It has to be unique all the
    same: a bucket is keyed `param-value`, so two facets sharing a param would
    put one row in both of them. tests/test_facets.py holds them apart.
    """

    label: str
    param: str
    field: str
    buckets: tuple[Range | Term, ...]

    def key(self, bucket: Range | Term) -> str:
        """How this bucket is named outside Python."""
        return f"{self.param}-{bucket.value}"

    def holds(self, bucket: Range | Term, values: dict[str, Any]) -> bool:
        """Whether a row projected by ``row_values`` falls in this bucket."""
        return bucket.holds(values[self.field])


# Variables and Constraints describe any linear program, so both subsets share
# one definition rather than each carrying a copy that could drift.
_SIZE_FACETS = (
    Facet(
        "Variables",
        "vars",
        "n_vars",
        (
            Range("under 50 K", "lt50k", hi=50_000),
            Range("50 K – 500 K", "50k-500k", lo=50_000, hi=500_000),
            Range("over 500 K", "gt500k", lo=500_000),
        ),
    ),
    Facet(
        "Constraints",
        "cons",
        "n_cons",
        (
            Range("under 10 K", "lt10k", hi=10_000),
            Range("10 K – 100 K", "10k-100k", lo=10_000, hi=100_000),
            Range("over 100 K", "gt100k", lo=100_000),
        ),
    ),
)

FACETS: dict[Subset, tuple[Facet, ...]] = {
    "primal": (
        *_SIZE_FACETS,
        Facet(
            "Depth",
            "depth",
            "depth",
            (
                Range("under 50", "lt50", hi=50),
                Range("50 – 250", "50-250", lo=50, hi=250),
                Range("over 250", "gt250", lo=250),
            ),
        ),
    ),
    "dual": (
        *_SIZE_FACETS,
        Facet(
            "What was relaxed",
            "relax",
            "relaxation",
            (
                Term("variable bounds only", "bounds-only"),
                Term("bounds and constraints", "bounds-rows"),
                Term("unbounded as given", "natural"),
            ),
        ),
        Facet(
            "Relaxation size",
            "size",
            "total_dropped",
            (
                Range("nothing removed", "0", hi=1),
                Range("1 – 5 elements", "1-5", lo=1, hi=6),
                Range("6 – 50", "6-50", lo=6, hi=51),
                Range("over 50", "gt50", lo=51),
            ),
        ),
    ),
}


def _relaxation(sample: Sample) -> str | None:
    """Which of the three ways a dual-infeasible instance was produced.

    A category of the instance rather than a bucket of a continuum, so the row
    carries it as a value. The three are mutually exclusive: an instance that
    was already unbounded had nothing removed. One that matches none of them is
    left unclassified rather than folded into the nearest.
    """
    p = sample.dual
    if p.natural_unbounded:
        return "natural"
    if p.rows_dropped > 0:
        return "bounds-rows"
    if p.bounds_dropped > 0:
        return "bounds-only"
    return None


def row_values(sample: Sample) -> dict[str, Any]:
    """Return the fields used to display, sort and filter one browse row."""
    values: dict[str, Any] = {
        "instance": sample.instance,
        "n_vars": sample.n_vars,
        "n_cons": sample.n_cons,
        "nnz": sample.nnz,
        "file_bytes": sample.file_bytes,
    }
    values["tags"] = [t for t in sample.tags if t not in NON_LP_TAGS]
    if sample.subset == "primal":
        values["depth"] = sample.primal.depth
        values["bound_changes"] = sample.primal.bound_changes
    else:
        values["bounds_dropped"] = sample.dual.bounds_dropped
        values["rows_dropped"] = sample.dual.rows_dropped
        values["total_dropped"] = sample.dual.total_dropped
        values["relaxation"] = _relaxation(sample)
    return values


def _tag_facet(rows: list[dict[str, Any]]) -> Facet | None:
    """The tag group these rows support, most common first."""
    counts: dict[str, int] = {}
    for values in rows:
        for tag in values["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    kept = sorted(
        ((t, n) for t, n in counts.items() if n >= TAG_FACET_MIN),
        key=lambda pair: (-pair[1], pair[0]),
    )
    if not kept:
        return None
    return Facet(
        "Structure (MIPLIB)",
        "tag",
        "tags",
        tuple(Term(tag, tag) for tag, _ in kept),
    )


def facets_for(subset: Subset, rows: list[dict[str, Any]]) -> list[Facet]:
    """Every facet these rows are offered, the fixed ones first."""
    tags = _tag_facet(rows)
    return [*FACETS[subset], *([tags] if tags else [])]


def memberships_for(facets: list[Facet], values: dict[str, Any]) -> tuple[str, ...]:
    """Materialise every offered bucket a row belongs to.

    This is the only evaluation of range and term semantics that crosses the
    Python/browser boundary. The client receives stable keys and performs set
    intersection; it does not carry a second implementation of ``holds``.
    """
    return tuple(
        facet.key(bucket)
        for facet in facets
        for bucket in facet.buckets
        if facet.holds(bucket, values)
    )
