"""The one script that reads the published dataset, rather than the index."""

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_site_index as X

from website import load as L
from website.records import HEAD_LIMIT


def _sidecar(root, subdir, stem, meta, payload=b"NAME\nENDATA\n"):
    d = root / subdir
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.mps.gz").write_bytes(gzip.compress(payload))
    (d / f"{stem}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


@pytest.fixture
def dataset(tmp_path):
    """A dataset on disk, in the shape the miners leave behind."""
    _sidecar(tmp_path, "infeasible", "bbb_if", {
        "instance": "bbb", "sample_kind": "pruned_infeasible_sibling",
        "n_vars": 10, "n_cons": 4, "nnz": 20, "depth": 3,
        "branch_var": 1, "branch_sense": ">=", "branch_value": 2.0,
        "path_entries": [f"x{i}<=0" for i in range(50)], "sha256": "ab" * 32})
    _sidecar(tmp_path, "unbounded", "aaa_ub", {
        "instance": "aaa", "sample_kind": "lp_unbounded_after_drop",
        "n_vars": 7, "n_cons": 1, "nnz": 5, "natural_unbounded": False,
        "drops": [{"kind": "row", "row": 0, "name": "c0"}], "sha256": "cd" * 32})
    return tmp_path


def test_index_round_trips_into_the_samples_the_site_renders(dataset, tmp_path):
    records = X.scan(dataset)
    out = tmp_path / "site-index.json"
    out.write_text(json.dumps({"version": 1, "records": records}), encoding="utf-8")
    by_key = {(s.subset, s.instance): s for s in L.load_index(out)}
    assert set(by_key) == {("primal", "bbb"), ("dual", "aaa")}
    assert by_key[("primal", "bbb")].primal.depth == 3
    assert by_key[("dual", "aaa")].dual.rows_dropped == 1


def test_long_provenance_is_truncated_but_its_length_is_kept(dataset):
    """The whole bound box is what makes the sidecars 146 MB; the pages show the
    first twelve entries and the count, so only those go in the index."""
    rec = next(r for r in X.scan(dataset) if r["subset"] == "primal")
    assert rec["provenance"]["bound_changes"] == 50
    assert len(rec["provenance"]["path_head"]) == HEAD_LIMIT


def test_sizes_are_measured_from_the_files(dataset):
    for rec in X.scan(dataset):
        assert rec["file_bytes"] > 0 and rec["meta_bytes"] > 0


def test_a_sidecar_with_no_published_file_beside_it_stops_the_scan(dataset):
    (dataset / "infeasible" / "bbb_if.mps.gz").unlink()
    with pytest.raises(SystemExit, match=r"no \.mps\.gz"):
        X.scan(dataset)


def test_a_sidecar_without_a_checksum_gets_one_computed(tmp_path):
    """Sidecars written before scripts/add_checksums.py existed still have to yield
    a complete index, since the CSVs publish the hash."""
    import hashlib
    payload = b"NAME\nENDATA\n"
    _sidecar(tmp_path, "infeasible", "ccc_if", {
        "instance": "ccc", "sample_kind": "pruned_infeasible_sibling",
        "n_vars": 5, "n_cons": 2, "nnz": 4, "depth": 1,
        "branch_var": 0, "branch_sense": "<=", "branch_value": 1.0,
        "path_entries": []}, payload=payload)
    (tmp_path / "unbounded").mkdir()
    rec = X.scan(tmp_path)[0]
    want = hashlib.sha256((tmp_path / "infeasible" / "ccc_if.mps.gz").read_bytes())
    assert rec["sha256"] == want.hexdigest()
