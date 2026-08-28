"""The site and release archives share one machine-readable catalogue."""

import sys
import zipfile

from scripts import build_release_archives as archives
from scripts.dataset import scan_dataset
from website import build as site
from website.domain import SUBSET_SPECS
from website.index import load_collection


def test_release_archives_contain_the_site_catalogue(index, tmp_path, monkeypatch):
    samples = load_collection(index)
    dataset = tmp_path / "dataset"
    for sample in samples:
        directory = dataset / SUBSET_SPECS[sample.subset].directory
        directory.mkdir(parents=True, exist_ok=True)
        for suffix in (".meta.json", ".mps.gz"):
            (directory / (sample.stem + suffix)).write_bytes(suffix.encode())

    built = tmp_path / "site"
    site.build(index, built)
    licence = tmp_path / "LICENSE"
    licence.write_text("notice", encoding="utf-8")
    out = tmp_path / "dist"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_release_archives.py",
            "--dataset-dir",
            str(dataset),
            "--index",
            str(index),
            "--out-dir",
            str(out),
            "--licence",
            str(licence),
        ],
    )

    archives.main()

    entries = scan_dataset(dataset)
    for subset, info in SUBSET_SPECS.items():
        csv_name = f"{info.slug}.csv"
        with zipfile.ZipFile(out / f"{info.slug}.zip") as archive:
            assert archive.namelist() == [
                "LICENSE",
                csv_name,
                *(name for _, name in archives.members(entries, subset)),
            ]
            assert archive.read(csv_name) == (built / csv_name).read_bytes()
