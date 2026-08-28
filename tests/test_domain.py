import pytest

from website.domain import (
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
