from dataclasses import replace

import pytest

from website.domain import (
    DomainError,
    DualProvenance,
    PrimalProvenance,
    Sample,
    collection_totals,
    subset_bytes,
    subset_for_kind,
)
from website.index import load_collection


def test_sample_kinds_map_to_subsets():
    assert subset_for_kind("pruned_infeasible_sibling") == "primal"
    assert subset_for_kind("lp_unbounded_after_drop") == "dual"


def test_unknown_sample_kind_is_rejected():
    with pytest.raises(ValueError):
        subset_for_kind("something_else")


def test_subset_follows_the_provenance_it_carries():
    """A sample cannot claim one subset while carrying the other's fields."""
    common = {
        "instance": "x",
        "n_vars": 1,
        "n_cons": 1,
        "nnz": 1,
        "file_bytes": 1,
        "meta_bytes": 1,
    }
    primal = Sample(
        **common,
        provenance=PrimalProvenance(
            depth=3, bound_changes=9, branch_sense=">=", branch_value=2.0, branch_var=0
        ),
    )
    dual = Sample(
        **common,
        provenance=DualProvenance(bounds_dropped=1, rows_dropped=0),
    )
    assert (primal.subset, dual.subset) == ("primal", "dual")
    assert primal.primal.depth == 3 and dual.dual.bounds_dropped == 1
    with pytest.raises(TypeError, match="not a dual sample"):
        _ = primal.dual
    with pytest.raises(TypeError, match="not a primal sample"):
        _ = dual.primal


def test_collection_totals(index):
    totals = collection_totals(load_collection(index))
    assert totals["n_samples"] == 3
    assert totals["counts"] == {"primal": 2, "dual": 1}
    assert totals["natural_unbounded"] == 0
    assert totals["max_vars"] == 10 and totals["max_cons"] == 4


def test_subset_bytes_count_both_files(index):
    """Subset archives contain both MPS files and sidecars."""
    samples = load_collection(index)
    sizes = subset_bytes(samples)
    for subset, total in sizes.items():
        rows = [sample for sample in samples if sample.subset == subset]
        assert total == sum(sample.file_bytes + sample.meta_bytes for sample in rows)
        assert total > sum(sample.file_bytes for sample in rows)


def test_totals_include_zero_for_a_missing_subset(index):
    samples = tuple(sample for sample in load_collection(index) if sample.subset == "primal")
    assert collection_totals(samples)["counts"] == {"primal": 2, "dual": 0}
    assert subset_bytes(samples)["dual"] == 0


def test_rounds_counts_what_the_search_tried_not_what_it_kept():
    """The greedy search removes far more than it leaves: 185 rounds against
    six retained is the median instance. One number cannot say both."""
    drops = DualProvenance(bounds_dropped=5, rows_dropped=1, rounds=171)
    assert drops.total_dropped == 6
    assert drops.rounds == 171


def test_rounds_cannot_be_fewer_than_what_survived_them():
    with pytest.raises(DomainError):
        DualProvenance(bounds_dropped=5, rows_dropped=1, rounds=3)


def test_a_relaxation_unbounded_as_given_ran_no_rounds():
    assert DualProvenance(0, 0, natural_unbounded=True, rounds=0).rounds == 0
    with pytest.raises(DomainError):
        DualProvenance(0, 0, natural_unbounded=True, rounds=4)


def test_rounds_may_be_unrecorded():
    """The published schema does not require n_rounds, so a sidecar without it
    is valid; absent is not the same fact as zero."""
    assert DualProvenance(bounds_dropped=5, rows_dropped=1).rounds is None


def test_only_a_primal_file_comes_out_of_a_search():
    """A dual file is a relaxation, not a node: it has no run behind it."""
    dual = Sample(
        instance="aaa",
        n_vars=7,
        n_cons=2,
        nnz=9,
        file_bytes=1,
        meta_bytes=1,
        provenance=DualProvenance(bounds_dropped=1, rows_dropped=0),
    )
    with pytest.raises(DomainError):
        replace(dual, search_nodes=10)
