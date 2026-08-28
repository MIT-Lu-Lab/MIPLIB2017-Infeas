import json
from copy import deepcopy

import pytest

from website.index import (
    INDEX_VERSION,
    SiteIndexError,
    from_record,
    load_collection,
    to_record,
    with_source_metadata,
)


def test_loads_every_sample_sorted_by_subset_then_instance(index):
    got = load_collection(index)
    assert [(s.subset, s.instance) for s in got] == [
        ("dual", "aaa"),
        ("primal", "aaa"),
        ("primal", "bbb"),
    ]


def test_an_explicit_missing_miplib_metadata_cache_is_refused(tmp_path, index):
    with pytest.raises(SiteIndexError, match="metadata cache does not exist"):
        load_collection(index, miplib_path=tmp_path / "absent.json")


def test_miplib_metadata_is_attached_by_instance(tmp_path, index):
    meta = tmp_path / "miplib.json"
    meta.write_text(
        json.dumps(
            {
                "aaa": {
                    "submitter": "A. Person",
                    "tags": ["precedence"],
                    "description": "d",
                    "group": "g",
                }
            }
        )
    )
    by_key = {
        (sample.subset, sample.instance): sample
        for sample in load_collection(index, miplib_path=meta)
    }
    assert by_key[("primal", "aaa")].submitter == "A. Person"
    assert by_key[("primal", "aaa")].tags == ("precedence",)
    # both halves of a pair derive from the same source instance
    assert by_key[("dual", "aaa")].submitter == "A. Person"
    assert by_key[("primal", "bbb")].submitter is None


@pytest.mark.parametrize("version", [INDEX_VERSION - 1, INDEX_VERSION + 1])
def test_an_unsupported_index_version_is_refused(tmp_path, version):
    """A version mismatch means the index and reader were not changed together."""
    p = tmp_path / "site-index.json"
    p.write_text(json.dumps({"version": version, "records": []}))
    with pytest.raises(SiteIndexError, match=r"[Rr]egenerate"):
        load_collection(p)


def test_an_empty_index_is_refused(tmp_path):
    p = tmp_path / "site-index.json"
    p.write_text(json.dumps({"version": INDEX_VERSION, "records": []}))
    with pytest.raises(SiteIndexError, match="no records"):
        load_collection(p)


def _rewrite_index(tmp_path, source, mutate):
    doc = json.loads(source.read_text(encoding="utf-8"))
    mutate(doc)
    path = tmp_path / "changed-index.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_duplicate_sample_keys_are_refused(tmp_path, index):
    def duplicate(doc):
        doc["records"].append(deepcopy(doc["records"][0]))

    path = _rewrite_index(tmp_path, index, duplicate)
    with pytest.raises(SiteIndexError, match="duplicate sample"):
        load_collection(path)


def test_case_only_page_path_collisions_are_refused(tmp_path, index):
    def collide(doc):
        record = deepcopy(next(r for r in doc["records"] if r["subset"] == "primal"))
        record["instance"] = record["instance"].upper()
        doc["records"].append(record)

    path = _rewrite_index(tmp_path, index, collide)
    with pytest.raises(SiteIndexError, match="case-insensitive page-path collision"):
        load_collection(path)


@pytest.mark.parametrize("value", [True, 10.0, "10"])
def test_index_integer_fields_are_not_coerced(tmp_path, index, value):
    def change(doc):
        doc["records"][0]["n_vars"] = value

    path = _rewrite_index(tmp_path, index, change)
    with pytest.raises(SiteIndexError, match="must be an integer"):
        load_collection(path)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ('{"version": 1, "version": 1, "records": []}', "duplicate object key"),
        ('{"version": NaN, "records": []}', "non-standard numeric constant"),
    ],
)
def test_non_standard_json_extensions_are_refused(tmp_path, document, message):
    path = tmp_path / "invalid-index.json"
    path.write_text(document, encoding="utf-8")
    with pytest.raises(SiteIndexError, match=message):
        load_collection(path)


def test_miplib_tags_must_be_an_array_of_strings(tmp_path, index):
    meta = tmp_path / "miplib.json"
    meta.write_text(json.dumps({"aaa": {"tags": "not-a-list"}}), encoding="utf-8")
    with pytest.raises(SiteIndexError, match="tags must be an array"):
        load_collection(index, miplib_path=meta)


def test_records_round_trip_through_the_index(index):
    """Anything omitted by the index codec is unavailable to the site build."""
    fields = {
        "primal": {
            "depth",
            "bound_changes",
            "branch_sense",
            "branch_value",
            "branch_var",
            "branch_var_name",
            "path_head",
        },
        "dual": {
            "bounds_dropped",
            "rows_dropped",
            "natural_unbounded",
            "drops_head",
        },
    }
    for sample in load_collection(index):
        record = to_record(sample)
        assert isinstance(record["provenance"], dict)
        assert set(record["provenance"]) == fields[sample.subset]
        assert from_record(record) == sample


def test_both_drop_shapes_round_trip(index):
    sample = next(sample for sample in load_collection(index) if sample.subset == "dual")
    record = to_record(sample)
    provenance = record["provenance"]
    assert isinstance(provenance, dict)
    provenance["bounds_dropped"] = 1
    provenance["drops_head"] = (
        {"kind": "bound", "var": 1, "side": "lb"},
        *provenance["drops_head"],
    )

    decoded = from_record(record)
    assert [set(drop) for drop in decoded.dual.drops_head] == [
        {"kind", "var", "side"},
        {"kind", "row", "name"},
    ]


def test_source_metadata_is_not_baked_into_records(index):
    """Refreshing MIPLIB metadata must not require rebuilding published files."""
    sample = load_collection(index)[0]
    assert sample.submitter is None and "submitter" not in to_record(sample)
    got = with_source_metadata(sample, {"submitter": "A. Person", "tags": ["x"]})
    assert got.submitter == "A. Person" and got.tags == ("x",)
    assert with_source_metadata(sample, None) is sample


def test_record_shape_is_versioned_and_rejects_unknown_fields(index):
    samples = load_collection(index)
    record = to_record(next(sample for sample in samples if sample.subset == "primal"))
    record["typo"] = 1
    with pytest.raises(ValueError, match="unknown fields"):
        from_record(record)

    record = to_record(next(sample for sample in samples if sample.subset == "dual"))
    provenance = record["provenance"]
    assert isinstance(provenance, dict)
    drops = provenance["drops_head"]
    assert isinstance(drops, tuple) and isinstance(drops[0], dict)
    drops[0]["typo"] = 1
    with pytest.raises(ValueError, match="unknown fields"):
        from_record(record)


@pytest.mark.parametrize("sha256", ["AB" * 32, "a" * 63, 123])
def test_record_sha256_has_the_same_canonical_shape(index, sha256):
    record = to_record(load_collection(index)[0])
    record["sha256"] = sha256
    with pytest.raises(ValueError, match="sha256"):
        from_record(record)
