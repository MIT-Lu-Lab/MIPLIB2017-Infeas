"""Counts a page states are counted, not written down.

Three sentences used to spell them out: the overview card said "Of the 105 root
LP relaxations, 103 become unbounded ... two are unbounded as given", the browse
blurb said "For 103", and the guide said "the 130 sources". All three were true
on the day they were written and nothing referred to them, so the day one of
them stopped being true nothing would have said so.
"""

import re
from pathlib import Path

import pytest

from website import content
from website.domain import collection_totals
from website.index import load_collection
from website.render import browse as B
from website.render import overview as O
from website.render import static as S

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "metadata" / "site-index.json"
MIPLIB = ROOT / "metadata" / "miplib_meta.json"


def _numbers(text: str) -> set[int]:
    return {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)}


def _states(said: str, n: int) -> bool:
    """A count of one is a word in a sentence, not a numeral."""
    return str(n) in said if n > 1 else ("one" in said or "the other" in said)


@pytest.mark.parametrize(
    ("count", "natural"),
    [(105, 2), (7, 3), (2, 1), (40, 0), (5, 5), (1, 0), (1, 1), (3, 1), (4, 2)],
)
def test_the_dual_sentence_states_the_counts_it_is_given(count, natural):
    """Derived, not coincidence: hand it other numbers and it says those."""
    said = content.dual_derivation(count, natural)
    constructed = count - natural
    if constructed and natural:
        assert _states(said, constructed), said
        assert _states(said, natural), said
        # the total is a back-reference; every page has just given it
        assert str(count) not in said, said
    else:
        assert said.startswith(("Each", "The one")), said
    # the collection's own figures must not survive in the wording
    if constructed != 103:
        assert "103" not in said
    assert "105" not in said


def test_the_card_and_the_blurb_carry_no_number_of_their_own():
    """Whatever they say about how the dual half divides, they say from one
    place. A literal here is a number no test can follow."""
    # the dual card has no fixed text at all: it is the derivation. Whatever is
    # written down carries no count but the year in "MIPLIB 2017".
    for copy in (content.SUBSET_SUMMARY, content.SUBSET_CARD, content.SUBSET_META_SUMMARY):
        for subset, said in copy.items():
            assert not _numbers(said) - {2017}, f"{subset}: {said!r}"


def test_the_guide_states_the_number_of_sources_it_is_given():
    assert "42" in S.render_guide(42)
    assert "130" not in S.render_guide(42)
    # one source reads as one source, not "the 1 sources"
    assert "the one source imported" in S.render_guide(1)


@pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")
def test_every_count_a_page_states_is_the_count_the_collection_has():
    samples = list(load_collection(INDEX, MIPLIB))
    totals = collection_totals(samples)
    dual = [s for s in samples if s.subset == "dual"]
    natural = sum(s.dual.natural_unbounded for s in dual)
    imported = len({s.instance for s in samples if s.imported_from})

    card = content.subset_card("dual", len(dual), natural)
    blurb = content.subset_summary("dual", len(dual), natural)
    for said in (card, blurb):
        assert str(len(dual) - natural) in said
        assert str(natural) in said
    # the total belongs to the page around them, and is on it
    assert str(len(dual)) in B.render_browse("dual", samples)
    assert str(len(dual)) in O.render_overview(totals)

    guide = S.render_guide(imported)
    assert f"the {imported} sources imported" in guide

    overview = O.render_overview(totals)
    assert str(totals["n_samples"]) in overview
    assert str(len(dual) - natural) in overview
    browse = B.render_browse("dual", samples)
    assert str(len(dual) - natural) in browse


@pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")
def test_the_notice_still_states_the_collection_it_describes():
    """LICENSE is written by hand and stays that way: a legal notice is not
    something to generate. But the counts in it are claims about the data, and
    a claim that has quietly stopped being true is worse in a notice than
    anywhere else on the site.
    """
    samples = list(load_collection(INDEX, MIPLIB))
    sources = {s.instance for s in samples}
    imported = {s.instance for s in samples if s.imported_from}
    from_imported = [s for s in samples if s.imported_from]

    notice = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert f"{len(imported)} of the {len(sources)} source instances" in notice
    assert f"{len(from_imported)} of the {len(samples)} published" in notice
