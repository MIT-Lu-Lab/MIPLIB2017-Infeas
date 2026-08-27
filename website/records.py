"""Pure derivation: one sidecar dict in, one Sample out. No I/O."""

from __future__ import annotations

from dataclasses import dataclass, replace

__all__ = ["HEAD_LIMIT", "INDEX_VERSION", "NON_LP_TAGS", "OTHER_SUBSET",
           "SUBSET_META", "DualProvenance",
           "PrimalProvenance", "Sample", "fmt_bytes", "fmt_int", "from_record",
           "sample_from_meta", "subset_of", "to_record", "with_source_metadata"]

# long provenance lists render only this many entries
HEAD_LIMIT = 12

# Bumped whenever to_record's shape changes, so a build refuses an index it
# would misread rather than rendering whatever the old keys happen to hold.
INDEX_VERSION = 1

SUBSET_META = {
    "primal": {
        "slug": "primal-infeasible", "label": "Primal-infeasible",
        "suffix": "_if", "dir": "infeasible", "kind": "pruned_infeasible_sibling",
        "tone": "p",
    },
    "dual": {
        "slug": "dual-infeasible", "label": "Dual-infeasible",
        "suffix": "_ub", "dir": "unbounded", "kind": "lp_unbounded_after_drop",
        "tone": "d",
    },
}
_KIND_TO_SUBSET = {v["kind"]: k for k, v in SUBSET_META.items()}

# the collection is a duality pair, so each subset has exactly one counterpart
OTHER_SUBSET = {"primal": "dual", "dual": "primal"}


def subset_of(meta: dict) -> str:
    """Map a sidecar's sample_kind to 'primal' or 'dual'."""
    kind = meta.get("sample_kind")
    if kind not in _KIND_TO_SUBSET:
        raise ValueError(f"unknown sample_kind {kind!r}")
    return _KIND_TO_SUBSET[kind]


# The published files are continuous LPs, so a tag naming a variable type is false
# of them, and MIPLIB's own benchmark-set membership says nothing about them either.
# The constraint-class tags describe row shapes, which survive the relaxation.
NON_LP_TAGS = frozenset({
    "binary", "mixed_binary", "integer_knapsack",     # no integer variables remain
    "benchmark", "benchmark_suitable",                # MIPLIB's benchmarking protocol
    "feasibility",                                    # source had no objective; ours do
})


@dataclass(frozen=True)
class PrimalProvenance:
    """The branch-and-bound node a primal-infeasible sample was taken from."""
    depth: int
    bound_changes: int
    branch_sense: str
    branch_value: float
    branch_var: int | None = None
    branch_var_name: str | None = None
    path_head: tuple = ()

    @property
    def branch_label(self) -> str:
        """How to name the branched column.

        The miners record a 0-based index. Printing that as a name would invent
        one, and on 23 instances collide with a real column called exactly that,
        so an unresolved index is labelled as an index.
        """
        return self.branch_var_name or f"column {self.branch_var}"


@dataclass(frozen=True)
class DualProvenance:
    """What was removed from a relaxation to leave its objective unbounded."""
    bounds_dropped: int
    rows_dropped: int
    natural_unbounded: bool = False
    drops_head: tuple = ()

    @property
    def total_dropped(self) -> int:
        return self.bounds_dropped + self.rows_dropped


@dataclass(frozen=True)
class Sample:
    """One published sample: the linear program, and how it was derived.

    The provenance is one of two shapes, and which one it is decides the subset.
    Keeping them apart is what lets a renderer that reads `depth` be given
    something that has one.
    """
    instance: str
    n_vars: int
    n_cons: int
    nnz: int
    file_bytes: int
    provenance: PrimalProvenance | DualProvenance
    meta_bytes: int = 0
    # MIPLIB 2017 metadata for the source instance, from metadata/miplib_meta.json
    submitter: str | None = None
    tags: tuple = ()
    source_description: str | None = None
    source_group: str | None = None
    sha256: str | None = None
    mps_url: str | None = None
    meta_url: str | None = None

    @property
    def subset(self) -> str:
        """Which half of the collection this belongs to.

        Read off the provenance rather than stored beside it, so that a sample
        cannot claim one subset while carrying the other's fields.
        """
        return "primal" if isinstance(self.provenance, PrimalProvenance) else "dual"

    @property
    def primal(self) -> PrimalProvenance:
        """The provenance, as a primal one.

        The primal entries in the facets, the table columns and the CSV index are
        only ever applied to primal rows. Going through here says so where a type
        checker can see it, and turns a mis-dispatch into an error that names the
        instance instead of a None several calls further on.
        """
        if not isinstance(self.provenance, PrimalProvenance):
            raise TypeError(f"{self.instance} is not a primal sample")
        return self.provenance

    @property
    def dual(self) -> DualProvenance:
        """The provenance, as a dual one. See `primal`."""
        if not isinstance(self.provenance, DualProvenance):
            raise TypeError(f"{self.instance} is not a dual sample")
        return self.provenance

    @property
    def total_bytes(self) -> int:
        """Both published files. This is what an archive of the instance holds."""
        return self.file_bytes + self.meta_bytes

    @property
    def stem(self) -> str:
        return self.instance + SUBSET_META[self.subset]["suffix"]

    @property
    def page_path(self) -> str:
        return f"{SUBSET_META[self.subset]['slug']}/{self.instance}/"

    @property
    def miplib_url(self) -> str:
        return f"https://miplib.zib.de/instance_details_{self.instance}.html"


def _provenance_from_meta(meta: dict, subset: str) -> PrimalProvenance | DualProvenance:
    if subset == "primal":
        path = list(meta.get("path_entries", []))
        return PrimalProvenance(
            depth=int(meta["depth"]),
            # the node's whole bound box, not just the decisions on the path to it
            bound_changes=len(path),
            branch_sense=meta["branch_sense"],
            branch_value=meta["branch_value"],
            branch_var=meta.get("branch_var"),
            branch_var_name=meta.get("branch_var_name"),
            path_head=tuple(meta.get("path_head_named") or path[:HEAD_LIMIT]),
        )
    drops = list(meta.get("drops", []))
    return DualProvenance(
        bounds_dropped=sum(1 for d in drops if d["kind"] == "bound"),
        rows_dropped=sum(1 for d in drops if d["kind"] == "row"),
        natural_unbounded=bool(meta.get("natural_unbounded", False)),
        drops_head=tuple(drops[:HEAD_LIMIT]),
    )


def sample_from_meta(meta: dict, file_bytes: int, meta_bytes: int = 0) -> Sample:
    """Build a Sample from one sidecar dict.

    Args:
        meta (dict): parsed sidecar JSON.
        file_bytes (int): size of the .mps.gz on disk.
        meta_bytes (int): size of the sidecar on disk.

    The source instance's MIPLIB metadata and the download URLs are attached
    later, by with_source_metadata and by the build's release prefix. Only what
    the dataset itself says belongs here.
    """
    return Sample(
        instance=meta["instance"],
        n_vars=int(meta["n_vars"]), n_cons=int(meta["n_cons"]), nnz=int(meta["nnz"]),
        file_bytes=file_bytes, meta_bytes=meta_bytes,
        provenance=_provenance_from_meta(meta, subset_of(meta)),
        sha256=meta.get("sha256"),
    )


def with_source_metadata(sample: Sample, miplib: dict | None) -> Sample:
    """Attach the source instance's MIPLIB 2017 entry.

    Kept apart from the sample itself so the two can be regenerated
    independently: re-fetching MIPLIB's tags does not need the 2.3 GB of
    published files, and rebuilding the index does not need the network.
    """
    m = miplib or {}
    return replace(sample, submitter=m.get("submitter"), tags=tuple(m.get("tags", ())),
                   source_description=m.get("description"), source_group=m.get("group"))


# The index is a committed file, reviewed in diffs, so the shape is written out
# rather than derived from the dataclass: a field renamed in Python must not
# silently rewrite 334 records.
_PROVENANCE_FIELDS = {
    "primal": ("depth", "bound_changes", "branch_sense", "branch_value",
               "branch_var", "branch_var_name", "path_head"),
    "dual": ("bounds_dropped", "rows_dropped", "natural_unbounded", "drops_head"),
}
_SAMPLE_FIELDS = ("instance", "n_vars", "n_cons", "nnz", "file_bytes", "meta_bytes",
                  "sha256")


def to_record(sample: Sample) -> dict:
    """Serialise the dataset-derived half of a Sample, for the site index."""
    p = sample.provenance
    return {**{f: getattr(sample, f) for f in _SAMPLE_FIELDS},
            "subset": sample.subset,
            "provenance": {f: getattr(p, f) for f in _PROVENANCE_FIELDS[sample.subset]}}


def from_record(record: dict) -> Sample:
    """Rebuild a Sample from one site-index record. Inverse of to_record."""
    subset = record["subset"]
    if subset not in _PROVENANCE_FIELDS:
        raise ValueError(f"{record.get('instance')!r}: unknown subset {subset!r}")
    fields = {f: record["provenance"][f] for f in _PROVENANCE_FIELDS[subset]}
    for seq in ("path_head", "drops_head"):
        if seq in fields:
            fields[seq] = tuple(fields[seq])
    cls = PrimalProvenance if subset == "primal" else DualProvenance
    return Sample(**{f: record[f] for f in _SAMPLE_FIELDS}, provenance=cls(**fields))


def fmt_int(n: int) -> str:
    """Thousands-separated integer."""
    return f"{int(n):,}"


def fmt_bytes(n: int) -> str:
    """Byte count as KB, MB or GB, matching what the site shows."""
    if n < 1024:
        return f"{n} B"
    mb = n / (1024 * 1024)
    if mb < 0.1:
        return f"{n / 1024:.0f} KB"
    if mb < 100:
        return f"{mb:.2f} MB"
    if mb < 1024:
        return f"{mb:.1f} MB"
    return f"{mb / 1024:.2f} GB"
