"""Published contracts have immutable semantic-versioned identities."""

import copy
import json
from pathlib import Path

import pytest

from scripts.release_contract import parse_manifest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "schema" / "meta.schema.json"
SIDECAR_V1 = ROOT / "schema" / "sidecar" / "1.0.0" / "meta.schema.json"
SIDECAR_NEWEST = ROOT / "schema" / "sidecar" / "1.1.0" / "meta.schema.json"
MANIFEST_V1 = ROOT / "schema" / "release-manifest" / "1.0.0" / "manifest.schema.json"
SHA_A = "a" * 64
SHA_B = "b" * 64


def test_the_unversioned_schema_is_the_newest_frozen_one():
    """`meta.schema.json` is the living copy; each directory beside it is a
    snapshot. They have to agree, or the URL a sidecar names and the URL a
    reader pins would say different things about the same document."""
    jsonschema = pytest.importorskip("jsonschema")
    living = json.loads(LEGACY.read_text(encoding="utf-8"))
    newest = json.loads(SIDECAR_NEWEST.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(newest)
    comparable = copy.deepcopy(newest)
    comparable["$id"] = living["$id"]
    comparable["title"] = living["title"]
    assert comparable == living
    assert newest["$id"].endswith("/schema/sidecar/1.1.0/meta.schema.json")


def test_an_earlier_version_keeps_saying_what_it_said():
    """1.0.0 is published at its own URL, so it is not edited in place: 1.0.1
    corrected it by being another document, and 1.1.0 added integrality. Which
    constraint moved is written down, so a version that quietly gains or loses
    one fails here."""
    jsonschema = pytest.importorskip("jsonschema")
    first = json.loads(SIDECAR_V1.read_text(encoding="utf-8"))
    newest = json.loads(SIDECAR_NEWEST.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(first)
    assert first["$id"].endswith("/schema/sidecar/1.0.0/meta.schema.json")
    moved = {
        name
        for name in set(first["properties"]) | set(newest["properties"])
        if first["properties"].get(name) != newest["properties"].get(name)
    }
    assert moved == {"instance", "integrality"}
    # 1.0.0 called any string a name, including one carrying a path separator
    assert "pattern" not in first["properties"]["instance"]
    assert "pattern" in newest["properties"]["instance"]


def test_release_manifest_schema_is_the_runtime_contract():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(MANIFEST_V1.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    document = {
        "manifest_version": "1.0.0",
        "dataset": "MIPLIB2017-Infeas",
        "release": {"tag": "v1.0.1", "source_commit": "c" * 40},
        "sidecar_schema": "meta.schema.json",
        "artifacts": [
            {"name": "meta.schema.json", "role": "schema", "bytes": 5, "sha256": SHA_A},
            {"name": "LICENSE.txt", "role": "notice", "bytes": 7, "sha256": SHA_B},
            {"name": "verify-published.csv", "role": "verification", "bytes": 9, "sha256": SHA_A},
        ],
    }

    validator = jsonschema.Draft202012Validator(schema)
    assert not list(validator.iter_errors(document))
    assert parse_manifest(document).tag == "v1.0.1"

    integer_as_float = copy.deepcopy(document)
    integer_as_float["artifacts"][0]["bytes"] = 5.0
    assert parse_manifest(integer_as_float).artifacts[0].size == 5

    string_paths = (
        ("release", "tag"),
        ("release", "source_commit"),
        ("sidecar_schema",),
        ("artifacts", 0, "name"),
        ("artifacts", 0, "sha256"),
    )
    for path in string_paths:
        trailing_newline = copy.deepcopy(document)
        parent = trailing_newline
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] += "\n"
        with pytest.raises(ValueError):
            parse_manifest(trailing_newline)

    document["license"] = "CC-BY-SA-4.0"
    with pytest.raises(ValueError, match="license"):
        parse_manifest(document)


def test_manifest_schema_requires_notice_and_one_verification_report():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(MANIFEST_V1.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    base = {
        "manifest_version": "1.0.0",
        "dataset": "MIPLIB2017-Infeas",
        "release": {"tag": "v1.0.1", "source_commit": "c" * 40},
        "sidecar_schema": "meta.schema.json",
        "artifacts": [
            {"name": "meta.schema.json", "role": "schema", "bytes": 5, "sha256": SHA_A},
        ],
    }
    assert list(validator.iter_errors(base))

    base["artifacts"].extend(
        [
            {"name": "LICENSE.txt", "role": "notice", "bytes": 7, "sha256": SHA_B},
            {"name": "first.csv", "role": "verification", "bytes": 9, "sha256": SHA_A},
            {"name": "second.csv", "role": "verification", "bytes": 10, "sha256": SHA_B},
        ]
    )
    assert list(validator.iter_errors(base))
