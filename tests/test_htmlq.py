"""The query the other tests ask their questions through.

What is checked here is this module's own behaviour. Parsing belongs to
BeautifulSoup: entities, void elements and unclosed tags are its contract, and
restating them here would be testing somebody else's library.
"""

import pytest

from tests.htmlq import page

SAMPLE = """
<div class="browse">
  <details class="facets" open>
    <summary><span>Filters</span><span class="facet-selected">None selected</span></summary>
    <fieldset class="facet"><legend class="eyebrow">Variables</legend>
      <label><input type="checkbox" data-k="vars-lt50k"> under 50 K <span class="n">7</span></label>
      <label><input type="checkbox" data-k="vars-gt500k"> over 500 K
        <span class="n">2</span></label>
    </fieldset>
  </details>
  <table>
    <caption id="cap" class="sr-only">Primal-infeasible instances</caption>
    <thead><tr><th scope="col"><button data-sort="instance">Instance</button></th></tr></thead>
    <tbody><tr><th scope="row" class="name"><a href="aaa/">aaa</a></th></tr></tbody>
  </table>
</div>
"""


def test_finds_by_tag_class_and_attribute():
    root = page(SAMPLE)
    assert root.one("details.facets").has("open")
    assert root.one("caption").get("id") == "cap"
    assert len(root.all("input[data-k]")) == 2
    assert root.one('input[data-k="vars-gt500k"]').get("type") == "checkbox"


def test_a_class_selector_does_not_need_every_class():
    assert page(SAMPLE).one("caption.sr-only").get("id") == "cap"


def test_selectors_are_ordinary_css():
    """Combinators and pseudo-classes come with the parser, so a test that
    needs one writes it rather than working around a home-made grammar."""
    assert page(SAMPLE).one("thead > tr > th").get("scope") == "col"
    assert page(SAMPLE).first("fieldset > label:nth-of-type(2)").text.startswith("over")


def test_text_gathers_descendants_and_normalises_space():
    label = page(SAMPLE).first("label")
    assert label.text == "under 50 K 7"
    assert page(SAMPLE).one("caption").text == "Primal-infeasible instances"


def test_children_are_the_elements_without_the_text_between_them():
    label = page(SAMPLE).first("label")
    assert [child.tag.name for child in label.children] == ["input", "span"]


def test_one_says_which_way_it_failed():
    root = page(SAMPLE)
    with pytest.raises(AssertionError, match="nothing matches"):
        root.one("form")
    with pytest.raises(AssertionError, match="2 elements match"):
        root.one("label")
