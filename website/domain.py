"""Published subset definitions, domain objects, and collection summaries."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict, cast

Subset = Literal["primal", "dual"]
SampleKind = Literal["pruned_infeasible_sibling", "lp_unbounded_after_drop"]


@dataclass(frozen=True)
class SubsetSpec:
    """Stable dataset, filename, and route names for one subset."""

    slug: str
    label: str
    suffix: str
    directory: str
    kind: SampleKind
    tone: str


SUBSET_SPECS: dict[Subset, SubsetSpec] = {
    "primal": SubsetSpec(
        slug="primal-infeasible",
        label="Primal-infeasible",
        suffix="_if",
        directory="infeasible",
        kind="pruned_infeasible_sibling",
        tone="p",
    ),
    "dual": SubsetSpec(
        slug="dual-infeasible",
        label="Dual-infeasible",
        suffix="_ub",
        directory="unbounded",
        kind="lp_unbounded_after_drop",
        tone="d",
    ),
}

_KIND_TO_SUBSET: dict[SampleKind, Subset] = {
    spec.kind: subset for subset, spec in SUBSET_SPECS.items()
}
OTHER_SUBSET: dict[Subset, Subset] = {"primal": "dual", "dual": "primal"}


def subset_for_kind(kind: object) -> Subset:
    """Return the subset for an exact, known ``sample_kind`` value."""

    if not isinstance(kind, str) or kind not in _KIND_TO_SUBSET:
        raise ValueError(f"unknown sample_kind {kind!r}")
    return _KIND_TO_SUBSET[cast(SampleKind, kind)]


HEAD_LIMIT = 12

BSD_LICENSED_SOURCE = "adult-max5features"
NOTICE_URL = "https://mit-lu-lab.github.io/MIPLIB2017-Infeas/LICENSE.txt"

_CC_BY_SA_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


class DomainError(ValueError):
    """A value cannot represent a safe, internally consistent site object."""


class SourceTerms(TypedDict):
    spdx: str | None
    summary: str
    notice: str
    miplib_import: NotRequired[str]


class BoundDrop(TypedDict):
    """The part of a dropped bound retained in the site index."""

    kind: Literal["bound"]
    var: int
    side: Literal["lb", "ub"]
    name: NotRequired[str]


class RowDrop(TypedDict):
    """The part of a dropped row retained in the site index."""

    kind: Literal["row"]
    row: int
    name: NotRequired[str]


Drop = BoundDrop | RowDrop


def source_terms(instance: str, imported_from: str | None) -> SourceTerms:
    """Return the source terms recorded for a MIPLIB instance."""

    if imported_from:
        return {
            "spdx": None,
            "summary": "No licence of record",
            "miplib_import": imported_from,
            "notice": NOTICE_URL,
        }
    if instance == BSD_LICENSED_SOURCE:
        return {
            "spdx": "BSD-3-Clause",
            "summary": "BSD 3-Clause",
            "notice": NOTICE_URL,
        }
    return {
        "spdx": "CC-BY-SA-4.0",
        "summary": "CC BY-SA 4.0",
        "notice": NOTICE_URL,
    }


@dataclass(frozen=True)
class PrimalProvenance:
    """The branch-and-bound node a primal-infeasible sample came from."""

    depth: int
    bound_changes: int
    branch_sense: Literal[">=", "<="]
    branch_value: float
    branch_var: int
    branch_var_name: str | None = None
    path_head: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.branch_value) or not self.branch_value.is_integer():
            raise DomainError("branch_value must be an integer-valued finite number")
        if len(self.path_head) > HEAD_LIMIT:
            raise DomainError(f"path_head cannot contain more than {HEAD_LIMIT} entries")
        if len(self.path_head) > self.bound_changes:
            raise DomainError("path_head cannot be longer than bound_changes")

    @property
    def branch_label(self) -> str:
        return self.branch_var_name or f"column {self.branch_var}"


@dataclass(frozen=True)
class DualProvenance:
    """What was removed from a relaxation to leave its objective unbounded."""

    bounds_dropped: int
    rows_dropped: int
    natural_unbounded: bool = False
    drops_head: tuple[Drop, ...] = ()
    # How many rounds the greedy search ran, against what survived its pruning
    # pass: the median instance tried 185 and kept six. None where the sidecar
    # does not say, which the published schema permits and which is not zero.
    rounds: int | None = None

    def __post_init__(self) -> None:
        if self.rounds is not None:
            if self.rounds < self.total_dropped:
                raise DomainError("rounds cannot be fewer than the removals that survived them")
            if self.natural_unbounded and self.rounds:
                raise DomainError("a relaxation unbounded as given ran no rounds")
        if len(self.drops_head) > HEAD_LIMIT:
            raise DomainError(f"drops_head cannot contain more than {HEAD_LIMIT} entries")
        if len(self.drops_head) > self.total_dropped:
            raise DomainError("drops_head cannot be longer than the total number dropped")
        if self.natural_unbounded and self.total_dropped:
            raise DomainError("a natural-unbounded sample cannot contain removals")

        head_bounds = 0
        head_rows = 0
        for position, drop in enumerate(self.drops_head):
            kind = drop["kind"]
            if kind == "bound":
                head_bounds += 1
            elif kind == "row":
                head_rows += 1
            else:
                raise DomainError(f"drops_head[{position}].kind is unknown: {kind!r}")
        if head_bounds > self.bounds_dropped or head_rows > self.rows_dropped:
            raise DomainError("drops_head kinds disagree with the aggregate drop counts")

    @property
    def total_dropped(self) -> int:
        return self.bounds_dropped + self.rows_dropped


def validate_drop_indices(drops: Sequence[Drop], *, n_vars: int, source_rows: int) -> None:
    """Require every retained drop index to address its source relaxation."""

    for position, drop in enumerate(drops):
        if drop["kind"] == "bound" and drop["var"] >= n_vars:
            raise DomainError(f"drops[{position}].var must be below n_vars")
        if drop["kind"] == "row" and drop["row"] >= source_rows:
            raise DomainError(f"drops[{position}].row must be below the source row count")


@dataclass(frozen=True)
class Sample:
    """One published LP together with its derivation and source metadata."""

    instance: str
    n_vars: int
    n_cons: int
    nnz: int
    file_bytes: int
    meta_bytes: int
    provenance: PrimalProvenance | DualProvenance
    submitter: str | None = None
    tags: tuple[str, ...] = ()
    source_description: str | None = None
    source_group: str | None = None
    imported_from: str | None = None
    sha256: str | None = None
    # Nodes the branch-and-bound run processed, from the miners' log rather
    # than from the file: how much searching found this node, which its depth
    # does not say. Only a primal file comes out of such a run.
    search_nodes: int | None = None

    def __post_init__(self) -> None:
        if self.search_nodes is not None:
            if self.subset != "primal":
                raise DomainError("only a primal-infeasible file comes from a search")
            if self.search_nodes < 1:
                raise DomainError("a search that produced a file processed at least one node")
        if (
            isinstance(self.provenance, PrimalProvenance)
            and self.provenance.branch_var >= self.n_vars
        ):
            raise DomainError("branch_var must be a 0-based index below n_vars")

    @property
    def subset(self) -> Subset:
        return "primal" if isinstance(self.provenance, PrimalProvenance) else "dual"

    @property
    def primal(self) -> PrimalProvenance:
        if not isinstance(self.provenance, PrimalProvenance):
            raise TypeError(f"{self.instance} is not a primal sample")
        return self.provenance

    @property
    def dual(self) -> DualProvenance:
        if not isinstance(self.provenance, DualProvenance):
            raise TypeError(f"{self.instance} is not a dual sample")
        return self.provenance

    @property
    def total_bytes(self) -> int:
        return self.file_bytes + self.meta_bytes

    @property
    def stem(self) -> str:
        return self.instance + SUBSET_SPECS[self.subset].suffix

    @property
    def page_path(self) -> str:
        return f"{SUBSET_SPECS[self.subset].slug}/{self.instance}/"

    @property
    def miplib_url(self) -> str:
        return f"https://miplib.zib.de/instance_details_{self.instance}.html"

    @property
    def source_terms_display(self) -> tuple[str, str | None]:
        """The source terms as a page label and optional canonical link."""

        terms = source_terms(self.instance, self.imported_from)
        spdx = terms["spdx"]
        url = _CC_BY_SA_URL if spdx == "CC-BY-SA-4.0" else None
        return terms["summary"], url


class CollectionTotals(TypedDict):
    n_samples: int
    counts: dict[Subset, int]
    natural_unbounded: int
    max_vars: int
    max_cons: int


def collection_totals(samples: Sequence[Sample]) -> CollectionTotals:
    """Return the headline figures used by overview and download pages."""

    if not samples:
        raise DomainError("cannot total an empty sample collection")
    counts: dict[Subset, int] = dict.fromkeys(SUBSET_SPECS, 0)
    for sample in samples:
        counts[sample.subset] += 1
    return {
        "n_samples": len(samples),
        "counts": counts,
        "natural_unbounded": sum(
            sample.subset == "dual" and sample.dual.natural_unbounded for sample in samples
        ),
        "max_vars": max(sample.n_vars for sample in samples),
        "max_cons": max(sample.n_cons for sample in samples),
    }


def subset_bytes(samples: Sequence[Sample]) -> dict[Subset, int]:
    """Return bytes of both published files, grouped by subset."""

    result: dict[Subset, int] = dict.fromkeys(SUBSET_SPECS, 0)
    for sample in samples:
        result[sample.subset] += sample.total_bytes
    return result
