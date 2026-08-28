"""The properties one facet declaration and materialised memberships buy."""

import re
from pathlib import Path

import pytest

from website.index import load_collection
from website.render import browse as B
from website.render import facets as F

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "metadata" / "site-index.json"


@pytest.fixture(params=["primal", "dual"])
def subset(request):
    return request.param


def _values(index, subset):
    return [F.row_values(sample) for sample in load_collection(index) if sample.subset == subset]


def test_a_range_facet_puts_every_row_in_exactly_one_bucket(index, subset):
    """Half-open bounds, so adjacent buckets meet at one number rather than
    overlapping on it or leaving it out."""
    for values in _values(index, subset):
        for facet in F.facets_for(subset, [values]):
            if not all(isinstance(b, F.Range) for b in facet.buckets):
                continue
            held = [b for b in facet.buckets if facet.holds(b, values)]
            assert len(held) == 1, f"{facet.param}: {values} matched {held}"


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


@pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")
def test_the_rail_the_declaration_and_the_payload_agree(subset):
    """Rail counts and shipped keys are two views of one Python evaluation."""
    from tests.test_render_browse import payload

    samples = [s for s in load_collection(INDEX) if s.subset == subset]
    html = B.render_browse(subset, samples)
    values = [F.row_values(s) for s in samples]
    shipped = payload(html)
    # the pairing the script relies on: one shipped record per rendered row, in
    # order, which is also what it refuses to start without
    assert [row["values"]["instance"] for row in shipped["rows"]] == [
        value["instance"] for value in values
    ]

    declared = {f.param: f for f in F.facets_for(subset, values)}
    memberships = [set(row["matches"]) for row in shipped["rows"]]
    for facet in declared.values():
        for bucket in facet.buckets:
            key = facet.key(bucket)
            printed = re.search(
                rf'data-k="{re.escape(key)}"[^>]*>[^<]*<span class="n">(\d+)</span>',
                html,
            )
            assert printed, f"{key} is not offered in the rail"

            by_declaration = sum(1 for value in values if facet.holds(bucket, value))
            by_payload = sum(key in row for row in memberships)
            assert int(printed.group(1)) == by_declaration == by_payload
