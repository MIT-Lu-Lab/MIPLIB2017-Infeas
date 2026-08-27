import pytest
from website import records as R


def _primal_meta(**over):
    meta = {
        "instance": "30n20b8", "sample_kind": "pruned_infeasible_sibling",
        "n_vars": 18380, "n_cons": 576, "nnz": 109706,
        "depth": 413, "parent_depth": 412,
        "branch_var": 643, "branch_sense": ">=", "branch_value": 29.0,
        "path_entries": [f"x{i}<=0" for i in range(50)],
    }
    meta.update(over)
    return meta


def _dual_meta(**over):
    meta = {
        "instance": "30n20b8", "sample_kind": "lp_unbounded_after_drop",
        "n_vars": 18380, "n_cons": 572, "nnz": 107150,
        "natural_unbounded": False,
        "drops": ([{"kind": "bound", "side": "lb", "var": j} for j in range(4)]
                  + [{"kind": "row", "row": 7, "name": "c7"}]),
    }
    meta.update(over)
    return meta


def test_subset_of_maps_both_kinds():
    assert R.subset_of(_primal_meta()) == "primal"
    assert R.subset_of(_dual_meta()) == "dual"


def test_subset_of_rejects_unknown_kind():
    with pytest.raises(ValueError):
        R.subset_of({"sample_kind": "something_else"})


def test_primal_sample_derives_path_fields():
    s = R.sample_from_meta(_primal_meta(), 524288)
    assert s.subset == "primal"
    assert s.primal.depth == 413
    assert s.primal.bound_changes == 50
    assert s.primal.path_head == tuple(f"x{i}<=0" for i in range(12))
    assert s.stem == "30n20b8_if"
    assert s.page_path == "primal-infeasible/30n20b8/"
    assert s.miplib_url == "https://miplib.zib.de/instance_details_30n20b8.html"


def test_dual_sample_partitions_drops_by_kind():
    s = R.sample_from_meta(_dual_meta(), 512000)
    assert s.subset == "dual"
    assert (s.dual.bounds_dropped, s.dual.rows_dropped) == (4, 1)
    assert s.stem == "30n20b8_ub"
    assert s.page_path == "dual-infeasible/30n20b8/"


def test_natural_unbounded_sample_has_no_drops():
    s = R.sample_from_meta(_dual_meta(drops=[], natural_unbounded=True), 100)
    assert (s.dual.bounds_dropped, s.dual.rows_dropped,
            s.dual.natural_unbounded) == (0, 0, True)


def test_a_record_round_trips_through_the_index():
    """The index is what the build reads, so anything to_record drops is gone
    from the site whatever the sidecar said."""
    for meta in (_primal_meta(), _dual_meta()):
        s = R.sample_from_meta(meta, 4096, 512)
        assert R.from_record(R.to_record(s)) == s


def test_source_metadata_is_attached_separately_from_the_sample():
    """Re-fetching MIPLIB's tags must not need the published files, so it is
    not baked into the index."""
    s = R.sample_from_meta(_primal_meta(), 1)
    assert s.submitter is None and "submitter" not in R.to_record(s)
    got = R.with_source_metadata(s, {"submitter": "A. Person", "tags": ["x"]})
    assert got.submitter == "A. Person" and got.tags == ("x",)
    assert R.with_source_metadata(s, None).tags == ()


def test_formatters():
    assert R.fmt_int(20682487) == "20,682,487"
    assert R.fmt_bytes(524288) == "0.50 MiB"
    assert R.fmt_bytes(379956346) == "362.4 MiB"
    assert R.fmt_bytes(2445000000) == "2.28 GiB"
    assert R.fmt_bytes(1024 * 1024 * 1024 + 1024 * 1024) == "1.00 GiB"


def test_fmt_bytes_shows_bytes_below_a_kilobyte():
    """Seven published sidecars are under 512 B and used to render as "0 KiB"."""
    assert R.fmt_bytes(327) == "327 B"
    assert R.fmt_bytes(483) == "483 B"
    assert R.fmt_bytes(1024) == "1 KiB"


def test_subset_follows_the_provenance_it_carries():
    """A sample cannot claim one subset while carrying the other's fields: the
    subset is read off the provenance rather than stored beside it."""
    common = {"instance": "x", "n_vars": 1, "n_cons": 1, "nnz": 1, "file_bytes": 1}
    p = R.Sample(**common, provenance=R.PrimalProvenance(
        depth=3, bound_changes=9, branch_sense=">=", branch_value=2.0))
    d = R.Sample(**common, provenance=R.DualProvenance(bounds_dropped=1, rows_dropped=0))
    assert (p.subset, d.subset) == ("primal", "dual")
    assert p.primal.depth == 3 and d.dual.bounds_dropped == 1
    with pytest.raises(TypeError, match="not a dual sample"):
        _ = p.dual
    with pytest.raises(TypeError, match="not a primal sample"):
        _ = d.primal


def test_provenance_requires_the_fields_its_subset_needs():
    """Omitting one is a TypeError at construction, not a None that surfaces
    several calls deep inside a page."""
    with pytest.raises(TypeError):
        R.PrimalProvenance(depth=3)
    with pytest.raises(TypeError):
        R.DualProvenance(bounds_dropped=1)
