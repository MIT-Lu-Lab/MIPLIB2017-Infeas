import pytest

from website.sidecar import sample_from_meta


def _primal_meta(**over):
    meta = {
        "instance": "30n20b8",
        "sample_kind": "pruned_infeasible_sibling",
        "n_vars": 18380,
        "n_cons": 576,
        "nnz": 109706,
        "depth": 413,
        "parent_depth": 412,
        "branch_var": 643,
        "branch_sense": ">=",
        "branch_value": 29.0,
        "path_entries": [f"x{i}<=0" for i in range(50)],
    }
    meta.update(over)
    return meta


def _dual_meta(**over):
    meta = {
        "instance": "30n20b8",
        "sample_kind": "lp_unbounded_after_drop",
        "n_vars": 18380,
        "n_cons": 572,
        "nnz": 107150,
        "natural_unbounded": False,
        "drops": (
            [{"kind": "bound", "side": "lb", "var": j, "original_value": 0.0} for j in range(4)]
            + [{"kind": "row", "row": 7, "name": "c7", "original_sense": "L", "original_rhs": 1.0}]
        ),
    }
    meta.update(over)
    return meta


def test_primal_sample_derives_path_fields():
    s = sample_from_meta(_primal_meta(), 524288, 1)
    assert s.subset == "primal"
    assert s.primal.depth == 413
    assert s.primal.bound_changes == 50
    assert s.primal.path_head == tuple(f"x{i}<=0" for i in range(12))
    assert s.stem == "30n20b8_if"
    assert s.page_path == "primal-infeasible/30n20b8/"
    assert s.miplib_url == "https://miplib.zib.de/instance_details_30n20b8.html"


def test_dual_sample_partitions_drops_by_kind():
    s = sample_from_meta(_dual_meta(), 512000, 1)
    assert s.subset == "dual"
    assert (s.dual.bounds_dropped, s.dual.rows_dropped) == (4, 1)
    assert s.stem == "30n20b8_ub"
    assert s.page_path == "dual-infeasible/30n20b8/"


def test_natural_unbounded_sample_has_no_drops():
    s = sample_from_meta(_dual_meta(drops=[], natural_unbounded=True), 100, 1)
    assert (s.dual.bounds_dropped, s.dual.rows_dropped, s.dual.natural_unbounded) == (0, 0, True)


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_measured_byte_sizes_are_exact_integers(value):
    """File sizes do not come from the schema-validated sidecar."""
    with pytest.raises(ValueError, match=r"file_bytes must be an integer"):
        sample_from_meta(_primal_meta(), value, 1)


def test_derived_counts_must_agree_with_the_sidecar():
    with pytest.raises(ValueError, match="n_dropped"):
        sample_from_meta(_dual_meta(n_dropped=99), 1, 1)
