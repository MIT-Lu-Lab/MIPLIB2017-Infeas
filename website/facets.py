"""What a browse page can be filtered by, declared once.

A facet used to be four things that had to agree and were kept apart: a lambda
deciding which rows a bucket held, a string key naming that bucket on the wire
and marked "must not change once published", a count computed by a separate
expression over the same lambda, and the client-side matcher that consumed the
key. The boundary 50,000 lived in the lambda and its name lived in the string,
with nothing tying them together; a rail whose counts disagreed with what
filtering showed was prevented by care alone.

A bucket here states its own bounds. The rail, the counts, the row's tokens and
(next) the client's matcher all read the same declaration, so the disagreement
is not expressible.

The vocabulary is the ordinary one for faceted search: a range facet buckets a
numeric field into half-open intervals, a term facet selects values of a
categorical one. There is no third kind and no predicate language.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field

from .records import NON_LP_TAGS, Sample

__all__ = ["FACETS", "TAG_FACET_MIN", "Facet", "Range", "Term", "facets_for",
           "row_values"]

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

    def holds(self, value: object) -> bool:
        if not isinstance(value, (int, float)):
            return False
        return ((self.lo is None or value >= self.lo)
                and (self.hi is None or value < self.hi))

    def as_json(self) -> dict:
        bounds = {"lo": self.lo, "hi": self.hi}
        return {"kind": "range", "value": self.value,
                **{k: v for k, v in bounds.items() if v is not None}}


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

    def as_json(self) -> dict:
        return {"kind": "term", "value": self.value}


@dataclass(frozen=True)
class Facet:
    """One group of checkboxes: a label, the row field it reads, its buckets.

    `param` names the facet where a reader can see it, in a row's tokens and in
    the query string, so it is chosen to read well rather than to be unique.
    """

    label: str
    param: str
    field: str
    buckets: tuple[Range | Term, ...] = dataclass_field(default_factory=tuple)

    def key(self, bucket: Range | Term) -> str:
        """How this bucket is named outside Python."""
        return f"{self.param}-{bucket.value}"

    def holds(self, bucket: Range | Term, values: dict) -> bool:
        """Whether a row, projected by `row_values`, falls in this bucket.

        A field the row does not carry holds nothing: the dual facets are asked
        only about dual rows, and an unclassified row falls in no bucket rather
        than in the first one.
        """
        value = values.get(self.field)
        return value is not None and bucket.holds(value)

    def as_json(self) -> dict:
        """What the page ships so the client can evaluate the same buckets.

        The label stays behind: the rail is rendered by the build, and the
        client only has to decide which rows a checkbox selects.
        """
        return {"param": self.param, "field": self.field,
                "buckets": [b.as_json() for b in self.buckets]}


# Variables and Constraints describe any linear program, so both subsets share
# one definition rather than each carrying a copy that could drift.
_SIZE_FACETS = (
    Facet("Variables", "vars", "n_vars", (
        Range("under 50 K", "lt50k", hi=50_000),
        Range("50 K – 500 K", "50k-500k", lo=50_000, hi=500_000),
        Range("over 500 K", "gt500k", lo=500_000),
    )),
    Facet("Constraints", "cons", "n_cons", (
        Range("under 10 K", "lt10k", hi=10_000),
        Range("10 K – 100 K", "10k-100k", lo=10_000, hi=100_000),
        Range("over 100 K", "gt100k", lo=100_000),
    )),
)

FACETS: dict[str, tuple[Facet, ...]] = {
    "primal": (
        *_SIZE_FACETS,
        Facet("Depth", "depth", "depth", (
            Range("under 50", "lt50", hi=50),
            Range("50 – 250", "50-250", lo=50, hi=250),
            Range("over 250", "gt250", lo=250),
        )),
    ),
    "dual": (
        *_SIZE_FACETS,
        Facet("What was relaxed", "relax", "relaxation", (
            Term("variable bounds only", "bounds-only"),
            Term("bounds and constraints", "bounds-rows"),
            Term("unbounded as given", "natural"),
        )),
        Facet("Relaxation size", "size", "total_dropped", (
            Range("nothing removed", "0", hi=1),
            Range("1 – 5 elements", "1-5", lo=1, hi=6),
            Range("6 – 50", "6-50", lo=6, hi=51),
            Range("over 50", "gt50", lo=51),
        )),
    ),
}

# MIPLIB's tags vary by subset, so this group is built from the rows in hand.
_TAG_FACET = Facet("Structure (MIPLIB)", "tag", "tags")


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


def row_values(sample: Sample) -> dict:
    """Everything a browse page knows about one row.

    The facets read this, the table's sort keys come from it, and it is what the
    page ships to the client. One projection, so a field a filter can reach is a
    field the reader can see.
    """
    values: dict[str, object] = {
        "instance": sample.instance,
        "n_vars": sample.n_vars,
        "n_cons": sample.n_cons,
        "nnz": sample.nnz,
        "file_bytes": sample.file_bytes,
        "tags": [t for t in sample.tags if t not in NON_LP_TAGS],
    }
    if sample.subset == "primal":
        values["depth"] = sample.primal.depth
        values["bound_changes"] = sample.primal.bound_changes
    else:
        values["bounds_dropped"] = sample.dual.bounds_dropped
        values["rows_dropped"] = sample.dual.rows_dropped
        values["total_dropped"] = sample.dual.total_dropped
        values["relaxation"] = _relaxation(sample)
    return values


def _tag_facet(rows: list[dict]) -> Facet | None:
    """The tag group these rows support, most common first."""
    counts: dict[str, int] = {}
    for values in rows:
        for tag in values["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    kept = sorted(((t, n) for t, n in counts.items() if n >= TAG_FACET_MIN),
                  key=lambda pair: (-pair[1], pair[0]))
    if not kept:
        return None
    return Facet(_TAG_FACET.label, _TAG_FACET.param, _TAG_FACET.field,
                 tuple(Term(tag, tag) for tag, _ in kept))


def facets_for(subset: str, rows: list[dict]) -> list[Facet]:
    """Every facet these rows are offered, the fixed ones first."""
    tags = _tag_facet(rows)
    return [*FACETS[subset], *([tags] if tags else [])]
