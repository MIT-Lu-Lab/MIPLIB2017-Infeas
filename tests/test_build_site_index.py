"""The one script that reads the published dataset, rather than the index."""

import gzip
import json

import pytest

from scripts import build_site_index as X
from website.domain import HEAD_LIMIT
from website.index import INDEX_VERSION, load_collection
from website.sidecar import SidecarError


def _sidecar(root, subdir, stem, meta, payload=b"NAME\nENDATA\n"):
    d = root / subdir
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.mps.gz").write_bytes(gzip.compress(payload))
    (d / f"{stem}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


@pytest.fixture
def dataset(tmp_path):
    """A dataset on disk, in the shape the miners leave behind."""
    _sidecar(
        tmp_path,
        "infeasible",
        "bbb_if",
        {
            "instance": "bbb",
            "sample_kind": "pruned_infeasible_sibling",
            "n_vars": 10,
            "n_cons": 4,
            "nnz": 20,
            "depth": 3,
            "branch_var": 1,
            "branch_sense": ">=",
            "branch_value": 2.0,
            "path_entries": [f"x{i}<=0" for i in range(50)],
            "sha256": "ab" * 32,
        },
    )
    _sidecar(
        tmp_path,
        "unbounded",
        "aaa_ub",
        {
            "instance": "aaa",
            "sample_kind": "lp_unbounded_after_drop",
            "n_vars": 7,
            "n_cons": 1,
            "nnz": 5,
            "natural_unbounded": False,
            "drops": [
                {"kind": "row", "row": 0, "name": "c0", "original_sense": "L", "original_rhs": 1.0}
            ],
            "sha256": "cd" * 32,
        },
    )
    return tmp_path


def test_index_round_trips_into_the_samples_the_site_renders(dataset, tmp_path):
    records = X.scan(dataset)
    out = tmp_path / "site-index.json"
    out.write_text(json.dumps({"version": INDEX_VERSION, "records": records}), encoding="utf-8")
    by_key = {(s.subset, s.instance): s for s in load_collection(out)}
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


def test_a_sidecar_cannot_claim_a_different_instance_than_its_filename(dataset):
    path = dataset / "infeasible" / "bbb_if.meta.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["instance"] = "claimed"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(SystemExit, match="identity does not match"):
        X.scan(dataset)


def test_a_sidecar_without_a_checksum_stops_the_scan(tmp_path):
    payload = b"NAME\nENDATA\n"
    _sidecar(
        tmp_path,
        "infeasible",
        "ccc_if",
        {
            "instance": "ccc",
            "sample_kind": "pruned_infeasible_sibling",
            "n_vars": 5,
            "n_cons": 2,
            "nnz": 4,
            "depth": 1,
            "branch_var": 0,
            "branch_sense": "<=",
            "branch_value": 1.0,
            "path_entries": [],
        },
        payload=payload,
    )
    (tmp_path / "unbounded").mkdir()
    with pytest.raises(SystemExit, match=r"scripts\.add_checksums"):
        X.scan(tmp_path)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ('{"instance": "a", "instance": "b"}', "duplicate object key"),
        ('{"branch_value": NaN}', "non-standard numeric constant"),
    ],
)
def test_sidecars_are_read_as_strict_json(tmp_path, document, message):
    d = tmp_path / "infeasible"
    d.mkdir()
    (d / "bad_if.mps.gz").write_bytes(gzip.compress(b"NAME\nENDATA\n"))
    (d / "bad_if.meta.json").write_text(document, encoding="utf-8")
    (tmp_path / "unbounded").mkdir()

    with pytest.raises(SidecarError, match=message):
        X.scan(tmp_path)
