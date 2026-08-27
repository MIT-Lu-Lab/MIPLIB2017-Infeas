import json

import pytest

from website import load as L
from website.records import INDEX_VERSION


def test_loads_every_sample_sorted_by_subset_then_instance(index):
    got = L.load_index(index)
    assert [(s.subset, s.instance) for s in got] == [
        ("dual", "aaa"), ("primal", "aaa"), ("primal", "bbb")]


def test_both_file_sizes_survive_the_index(index):
    """The download card and the archive totals quote them, and the index is all
    the build has: the published files are not in the repository."""
    got = L.load_index(index)
    assert all(s.file_bytes > 0 and s.meta_bytes > 0 for s in got)


def test_no_urls_until_a_release_prefix_is_given(index):
    got = L.load_index(index)
    assert all(s.mps_url is None and s.meta_url is None for s in got)


def test_missing_miplib_metadata_is_not_fatal(tmp_path, index):
    got = L.load_index(index, miplib_path=tmp_path / "absent.json")
    assert all(s.submitter is None and s.tags == () for s in got)


def test_miplib_metadata_is_attached_by_instance(tmp_path, index):
    meta = tmp_path / "miplib.json"
    meta.write_text(json.dumps({"aaa": {"submitter": "A. Person", "tags": ["precedence"],
                                        "description": "d", "group": "g"}}))
    by_key = {(s.subset, s.instance): s for s in L.load_index(index, miplib_path=meta)}
    assert by_key[("primal", "aaa")].submitter == "A. Person"
    assert by_key[("primal", "aaa")].tags == ("precedence",)
    # both halves of a pair derive from the same source instance
    assert by_key[("dual", "aaa")].submitter == "A. Person"
    assert by_key[("primal", "bbb")].submitter is None


def test_an_index_from_a_later_version_is_refused(tmp_path):
    """Reading it with the old field names would render whatever they happen to
    hold rather than saying the index needs regenerating."""
    p = tmp_path / "site-index.json"
    p.write_text(json.dumps({"version": INDEX_VERSION + 1, "records": []}))
    with pytest.raises(SystemExit, match=r"[Rr]egenerate"):
        L.load_index(p)


def test_an_empty_index_is_refused(tmp_path):
    p = tmp_path / "site-index.json"
    p.write_text(json.dumps({"version": INDEX_VERSION, "records": []}))
    with pytest.raises(SystemExit, match="no records"):
        L.load_index(p)


def test_collection_totals(index):
    t = L.collection_totals(L.load_index(index))
    assert t["n_samples"] == 3
    assert t["counts"] == {"primal": 2, "dual": 1}
    assert t["max_vars"] == 10 and t["max_cons"] == 4


def test_subset_bytes_counts_both_files(index):
    """An archive of a subset holds the sidecars too, so its size is not the
    .mps.gz total the browse table sums."""
    samples = L.load_index(index)
    sizes = L.subset_bytes(samples)
    for subset, total in sizes.items():
        rows = [s for s in samples if s.subset == subset]
        assert total == sum(s.file_bytes + s.meta_bytes for s in rows)
        assert total > sum(s.file_bytes for s in rows)
