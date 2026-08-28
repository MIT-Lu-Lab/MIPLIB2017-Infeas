"""The catalogue a script reads, and the one a spreadsheet reads.

They are the same catalogue in two formats, from one definition in build.
These hold that they cannot come apart, and that a consumer can get from the
index to a file without a checkout.
"""

import csv
import json
from pathlib import Path

import pytest

from website import build as B
from website.catalog import FORMAT_VERSION

BASE = "https://example.invalid/dl/v1.0"
SITE = "https://example.invalid/mi/"


@pytest.fixture
def built(tmp_path, index):
    out = tmp_path / "published"
    B.build(index, out, release_base_url=BASE, site_url=SITE)
    return out


def _json(built: Path, name: str) -> dict:
    return json.loads((built / name).read_text(encoding="utf-8"))


def test_public_json_indexes_declare_their_format_version(built):
    assert _json(built, "index.json")["format_version"] == FORMAT_VERSION
    for slug in ("primal-infeasible", "dual-infeasible"):
        assert _json(built, f"{slug}.json")["format_version"] == FORMAT_VERSION


@pytest.mark.parametrize("slug", ["primal-infeasible", "dual-infeasible"])
def test_the_json_and_the_csv_are_the_same_catalogue(built, slug):
    """Same rows, same order, same fields. Two formats of one definition, so a
    column added to the CSV cannot go missing from what a script reads."""
    doc = _json(built, f"{slug}.json")
    with (built / f"{slug}.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(doc["instances"]) == doc["count"]
    for from_csv, from_json in zip(rows, doc["instances"], strict=True):
        assert list(from_csv) == list(from_json), "field names or their order"
        assert from_csv == {k: str(v) for k, v in from_json.items()}


@pytest.mark.parametrize("slug", ["primal-infeasible", "dual-infeasible"])
def test_a_count_is_a_number_in_the_json(built, slug):
    """The reason to publish it beside the CSV: a consumer does not have to
    decide what each column meant."""
    row = _json(built, f"{slug}.json")["instances"][0]
    for field in ("n_vars", "n_cons", "nnz", "file_bytes"):
        assert isinstance(row[field], int), field
    assert isinstance(row["instance"], str)


@pytest.mark.parametrize("slug", ["primal-infeasible", "dual-infeasible"])
def test_the_prefix_and_a_filename_compose_into_the_download(built, slug):
    """The whole workflow a consumer has: read the index, join, fetch."""
    doc = _json(built, f"{slug}.json")
    assert doc["release_base_url"] == BASE + "/"
    for row in doc["instances"]:
        url = doc["release_base_url"] + row["mps_filename"]
        assert url.startswith(BASE + "/")
        assert url.endswith(".mps.gz")
    page = built / slug / doc["instances"][0]["instance"] / "index.html"
    assert doc["release_base_url"] + doc["instances"][0]["mps_filename"] in page.read_text(
        encoding="utf-8"
    )


def test_the_collection_index_points_at_files_that_exist(built):
    doc = _json(built, "index.json")
    assert doc["instances"] == sum(s["count"] for s in doc["subsets"])
    for subset in doc["subsets"]:
        for key in ("index", "csv"):
            assert (built / subset[key]).is_file(), subset[key]
        assert _json(built, subset["index"])["count"] == subset["count"]
    for key in ("sidecar_schema", "notice"):
        assert (built / doc[key]).is_file(), doc[key]


def test_the_index_names_no_url_the_build_was_not_given(tmp_path, index):
    """As the canonical URL does not: a guessed prefix sends a consumer to a
    file that is not there."""
    out = tmp_path / "local"
    B.build(index, out)
    doc = _json(out, "index.json")
    assert "url" not in doc and "release_base_url" not in doc
    for slug in ("primal-infeasible", "dual-infeasible"):
        assert "release_base_url" not in _json(out, f"{slug}.json")
