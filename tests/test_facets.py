"""The properties one facet declaration buys.

Each of these used to hold only because four separate expressions agreed: a
lambda, the string that named it on the wire, the count taken over the lambda,
and the client matcher that consumed the string.
"""

import re
from pathlib import Path

import pytest

from website import facets as F, load as L
from website.render import browse as B

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "metadata" / "site-index.json"


@pytest.fixture(params=["primal", "dual"])
def subset(request):
    return request.param


def _values(index, subset):
    return [F.row_values(s) for s in L.load_index(index) if s.subset == subset]


def test_a_range_facet_puts_every_row_in_exactly_one_bucket(index, subset):
    """Half-open bounds, so adjacent buckets meet at one number rather than
    overlapping on it or leaving it out."""
    for values in _values(index, subset):
        for facet in F.facets_for(subset, [values]):
            if not all(isinstance(b, F.Range) for b in facet.buckets):
                continue
            held = [b for b in facet.buckets if facet.holds(b, values)]
            if values.get(facet.field) is None:
                assert not held, f"{facet.param}: a row without the field matched"
            else:
                assert len(held) == 1, f"{facet.param}: {values} matched {held}"


def test_a_bucket_key_names_its_facet_and_its_value(index, subset):
    for facet in F.facets_for(subset, _values(index, subset)):
        for bucket in facet.buckets:
            assert facet.key(bucket) == f"{facet.param}-{bucket.value}"


def test_every_field_a_facet_reads_is_a_field_a_row_carries(index, subset):
    """A facet naming a field no row has would silently select nothing."""
    values = _values(index, subset)
    carried = set(values[0])
    for facet in F.facets_for(subset, values):
        assert facet.field in carried, f"{facet.param} reads absent {facet.field}"


def test_every_column_reads_a_field_a_row_carries(index, subset):
    values = _values(index, subset)
    for column in B.COLUMNS[subset]:
        assert column.field in values[0], column.field


def test_the_query_grammar_is_unambiguous(index, subset):
    """A filtered view is addressable as param=value,value. Two facets sharing a
    param would share a key, and a comma or an ampersand inside one would split
    a name in half."""
    facets = F.facets_for(subset, _values(index, subset))
    params = [facet.param for facet in facets]
    assert len(params) == len(set(params)), params
    keys = [facet.key(bucket) for facet in facets for bucket in facet.buckets]
    assert len(keys) == len(set(keys)), keys
    for facet in facets:
        assert not set(facet.param) & set(",&=?#")
        assert facet.param not in ("q", "sort", "dir"), "reserved by search and sort"
        for bucket in facet.buckets:
            assert not set(bucket.value) & set(",&=?#"), bucket


def holds_as_the_client_would(bucket: dict, value) -> bool:
    """bucketHolds() from website/assets.py, in Python.

    The browser evaluates the serialised declaration, and no test here can run
    it. Writing its six lines out is what lets the two be compared: if the
    JavaScript and this drift, the shape of the payload is what has to change,
    and these tests fail with it.
    """
    if value is None:
        return False
    if bucket["kind"] == "term":
        if isinstance(value, (list, tuple)):
            return bucket["value"] in value
        return value == bucket["value"]
    return (("lo" not in bucket or value >= bucket["lo"])
            and ("hi" not in bucket or value < bucket["hi"]))


@pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")
def test_the_rail_the_declaration_and_the_payload_agree(subset):
    """The property the declaration exists for, across the serialisation. Three
    counts that used to be three expressions: what the rail prints, what the
    facet selects in Python, and what the client would select from the payload.
    """
    from tests.test_render_browse import payload

    samples = [s for s in L.load_index(INDEX) if s.subset == subset]
    html = B.render_browse(subset, samples)
    values = [F.row_values(s) for s in samples]
    shipped = payload(html)
    assert [row["instance"] for row in shipped["rows"]] == [v["instance"] for v in values]

    declared = {f.param: f for f in F.facets_for(subset, values)}
    for facet in shipped["facets"]:
        for bucket in facet["buckets"]:
            key = f"{facet['param']}-{bucket['value']}"
            printed = re.search(
                rf'data-k="{re.escape(key)}">[^<]*<span class="n">(\d+)</span>', html)
            assert printed, f"{key} is not offered in the rail"

            in_python = declared[facet["param"]]
            declared_bucket = next(b for b in in_python.buckets
                                   if b.value == bucket["value"])
            by_declaration = sum(1 for v in values
                                 if in_python.holds(declared_bucket, v))
            by_payload = sum(1 for row in shipped["rows"]
                             if holds_as_the_client_would(bucket,
                                                          row.get(facet["field"])))
            assert int(printed.group(1)) == by_declaration == by_payload, (
                f"{key}: rail {printed.group(1)}, declaration {by_declaration}, "
                f"payload {by_payload}")
