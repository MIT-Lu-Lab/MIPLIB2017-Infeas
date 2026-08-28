"""What a sidecar may be, and which of the two things says so.

`schema/meta.schema.json` is served from the site and named by every release
manifest, so it is what a reader validates a sidecar against. It used to be
restated in Python as well, and the two had drifted in both directions at once.
`sample_from_meta` now validates against that same document, so the shape is
described once.

Four rules are still Python's, because JSON Schema cannot express them, and
each one is marked below:

* a `number` in JSON Schema admits NaN and Infinity, and `json.loads` reads
  both literals;
* an `integer` in JSON Schema admits 1.0, and a count that arrived as a float
  would be written to the index as one and refused on the way back in;
* the published branch values are integer split bounds, which the page uses to
  reconstruct the complementary side without rounding;
* nothing in a schema can compare two fields, so a dropped column's index is
  checked against this sample's own column count.

Every case is run through the parser, which is the project's answer. A case
the schema is meant to catch is run through the schema too, so a constraint
quietly dropped from it fails here rather than on a reader's machine.
"""

import json
from pathlib import Path

import pytest

from website.sidecar import SidecarError, sample_from_meta

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "meta.schema.json"

SHA = "ab" * 32
BOUND = {"kind": "bound", "var": 0, "side": "lb", "original_value": 0.0}
ROW = {"kind": "row", "row": 0, "original_sense": "L", "original_rhs": 1.0}


def sidecar(**overrides) -> dict:
    """A sidecar both sides accept, before a case bends one field."""
    base = {
        "instance": "aaa",
        "sample_kind": "lp_unbounded_after_drop",
        "n_vars": 10,
        "n_cons": 5,
        "nnz": 20,
        "sha256": SHA,
        "natural_unbounded": False,
        "drops": [dict(BOUND)],
    }
    return {**base, **overrides}


def primal(**overrides) -> dict:
    base = sidecar(
        sample_kind="pruned_infeasible_sibling",
        depth=3,
        branch_var=1,
        branch_sense=">=",
        branch_value=29.0,
        path_entries=["x1>=29"],
    )
    base.pop("drops")
    base.pop("natural_unbounded")
    return {**base, **overrides}


# (name, document, is a valid sidecar, which of the two enforces it)
BY_SCHEMA, BY_PYTHON = "schema", "python"
CASES = [
    ("a dual sidecar as published", sidecar(), True, BY_SCHEMA),
    ("a primal sidecar as published", primal(), True, BY_SCHEMA),
    ("a row drop", sidecar(drops=[dict(ROW)]), True, BY_SCHEMA),
    (
        "an optional range on a row drop",
        sidecar(drops=[{**ROW, "original_range": 4.0}]),
        True,
        BY_SCHEMA,
    ),
    ("no range on a row drop", sidecar(drops=[{**ROW, "original_range": None}]), True, BY_SCHEMA),
    ("an instance name with a separator", sidecar(instance="a/b"), False, BY_SCHEMA),
    ("an instance name that climbs", sidecar(instance="../../etc/passwd"), False, BY_SCHEMA),
    ("an instance name that is empty", sidecar(instance=""), False, BY_SCHEMA),
    ("a program with no columns", sidecar(n_vars=0), False, BY_SCHEMA),
    ("a negative row count", sidecar(n_cons=-1), False, BY_SCHEMA),
    ("a digest of the wrong length", sidecar(sha256="abc"), False, BY_SCHEMA),
    ("a digest in capitals", sidecar(sha256=SHA.upper()), False, BY_SCHEMA),
    ("an unknown sample kind", sidecar(sample_kind="something_else"), False, BY_SCHEMA),
    (
        "a bound drop without the value it held",
        sidecar(drops=[{k: v for k, v in BOUND.items() if k != "original_value"}]),
        False,
        BY_SCHEMA,
    ),
    (
        "a row drop without the sense it had",
        sidecar(drops=[{k: v for k, v in ROW.items() if k != "original_sense"}]),
        False,
        BY_SCHEMA,
    ),
    ("a drop of neither kind", sidecar(drops=[{"kind": "column", "var": 0}]), False, BY_SCHEMA),
    (
        "a bound drop with a misspelt field",
        sidecar(drops=[{**BOUND, "orignal_value": 0.0}]),
        False,
        BY_SCHEMA,
    ),
    ("a branch on neither side", primal(branch_sense="=="), False, BY_SCHEMA),
    ("a negative depth", primal(depth=-1), False, BY_SCHEMA),
    ("a branch value that is not a number", primal(branch_value=float("nan")), False, BY_PYTHON),
    ("a non-integral branch value", primal(branch_value=2.5), False, BY_PYTHON),
    ("a column count that arrived as a float", sidecar(n_vars=10.0), False, BY_PYTHON),
    (
        "a dropped column past the last column",
        sidecar(n_vars=1, drops=[{**BOUND, "var": 5}]),
        False,
        BY_PYTHON,
    ),
    (
        "a dropped row past the last row",
        sidecar(n_cons=1, drops=[{**ROW, "row": 9}]),
        False,
        BY_PYTHON,
    ),
]


@pytest.fixture(scope="module")
def validator():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


@pytest.mark.parametrize(
    ("name", "document", "valid", "enforced_by"), CASES, ids=[case[0] for case in CASES]
)
def test_a_sidecar_is_what_the_schema_and_these_four_rules_say(
    validator, name, document, valid, enforced_by
):
    try:
        sample_from_meta(document, 4096, 512)
        by_parser = True
    except SidecarError, ValueError:
        by_parser = False
    assert by_parser is valid, f"the parser {'accepts' if by_parser else 'rejects'} {name}"

    by_schema = not list(validator.iter_errors(document))
    if enforced_by is BY_SCHEMA:
        said = "accepts" if by_schema else "rejects"
        assert by_schema is valid, f"the schema {said} {name}"
    else:
        # the point of the case: valid against the schema, refused all the same
        assert by_schema, f"the schema already rejects {name}, so this is not its gap"
