"""The published sidecars have a schema, not just a page describing them."""

import json
from pathlib import Path

import pytest

from tests.conftest import _SIDECARS

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "meta.schema.json"


@pytest.fixture(scope="module")
def validator():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def test_the_fixture_sidecars_validate(validator):
    for meta, _, _ in _SIDECARS:
        assert not list(validator.iter_errors(meta)), meta["instance"]


def test_a_primal_sidecar_without_its_branch_is_rejected(validator):
    """The subset decides which fields are required. Without that the schema would
    accept a primal file carrying dual fields, which is the shape bug the Sample
    split fixed in the generator."""
    meta = dict(_SIDECARS[0][0])
    del meta["branch_sense"]
    assert list(validator.iter_errors(meta))


def test_a_dual_sidecar_without_its_drops_is_rejected(validator):
    meta = {k: v for k, v in _SIDECARS[2][0].items() if k != "drops"}
    assert list(validator.iter_errors(meta))


def test_a_drop_must_be_one_shape_or_the_other(validator):
    """A bound drop names a column and a side; a row drop names a row and its
    original sense. An entry carrying both is a bug in whatever wrote it."""
    meta = json.loads(json.dumps(_SIDECARS[2][0]))
    meta["drops"] = [{"kind": "row", "row": 0, "name": "c0", "side": "lb"}]
    assert list(validator.iter_errors(meta))


def test_the_schema_covers_every_field_the_fixture_sidecars_carry():
    """A field the generator reads but the schema does not mention would let a
    sidecar drop it and still validate."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    named = set(schema["properties"])
    for meta, _, _ in _SIDECARS:
        assert set(meta) <= named, set(meta) - named
