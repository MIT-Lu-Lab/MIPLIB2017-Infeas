"""The maintenance commands share one definition of the dataset layout."""

import json

import pytest

from scripts.dataset import DatasetError, read_entry_sidecar, scan_dataset
from website.domain import SUBSET_SPECS, Subset


def _pair(root, subset: Subset, instance: str) -> None:
    spec = SUBSET_SPECS[subset]
    directory = root / spec.directory
    directory.mkdir(exist_ok=True)
    stem = instance + spec.suffix
    (directory / f"{stem}.mps.gz").write_bytes(b"mps")
    (directory / f"{stem}.meta.json").write_text("{}", encoding="utf-8")


def _both_directories(root) -> None:
    for spec in SUBSET_SPECS.values():
        (root / spec.directory).mkdir(exist_ok=True)


def test_scan_dataset_returns_paired_files_in_stable_order(tmp_path):
    _both_directories(tmp_path)
    _pair(tmp_path, "primal", "z")
    _pair(tmp_path, "primal", "a")
    _pair(tmp_path, "dual", "b")

    entries = scan_dataset(tmp_path)

    assert [(entry.subset, entry.instance) for entry in entries] == [
        ("primal", "a"),
        ("primal", "z"),
        ("dual", "b"),
    ]
    assert [entry.stem for entry in entries] == ["a_if", "z_if", "b_ub"]


def test_scan_dataset_rejects_an_unpaired_file(tmp_path):
    _both_directories(tmp_path)
    (tmp_path / "infeasible" / "a_if.mps.gz").write_bytes(b"mps")

    with pytest.raises(DatasetError, match="no sidecar"):
        scan_dataset(tmp_path)


def test_scan_dataset_requires_both_subset_directories(tmp_path):
    (tmp_path / "infeasible").mkdir()

    with pytest.raises(DatasetError, match="unbounded"):
        scan_dataset(tmp_path)


def test_scan_dataset_rejects_a_filename_for_the_wrong_subset(tmp_path):
    _both_directories(tmp_path)
    directory = tmp_path / "infeasible"
    (directory / "a_ub.mps.gz").write_bytes(b"mps")
    (directory / "a_ub.meta.json").write_text("{}", encoding="utf-8")

    with pytest.raises(DatasetError, match="does not carry the Primal-infeasible suffix"):
        scan_dataset(tmp_path)


def test_sidecar_identity_is_bound_to_its_dataset_entry(tmp_path):
    _both_directories(tmp_path)
    _pair(tmp_path, "primal", "a")
    entry = scan_dataset(tmp_path)[0]
    entry.sidecar.write_text(
        json.dumps(
            {
                "instance": "someone-else",
                "sample_kind": SUBSET_SPECS["primal"].kind,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatasetError, match="instance does not match"):
        read_entry_sidecar(entry)
