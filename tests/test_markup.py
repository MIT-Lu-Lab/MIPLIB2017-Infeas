"""The escaping boundary. These are the guarantees the renderers rely on."""

import pytest

from website.render import browse as B
from website.render.markup import Markup, attr, el, esc, fmt, join


def test_text_is_escaped_and_markup_is_not():
    assert esc('<a & "b">') == "&lt;a &amp; &quot;b&quot;&gt;"
    assert esc(Markup("<b>kept</b>")) == "<b>kept</b>"
    # escaping is idempotent, so a value cannot be double-escaped by passing
    # through two helpers
    assert esc(esc("<b>")) == "&lt;b&gt;"


def test_an_attribute_never_honours_markup():
    """Markup means "this is HTML"; inside an attribute that is meaningless, and
    trusting it there is how a quote would escape the attribute."""
    assert attr(Markup('" onclick="x')) == "&quot; onclick=&quot;x"


def test_element_escapes_children_and_attribute_values():
    assert el("p", "a < b") == "<p>a &lt; b</p>"
    assert el("a", "x", href='/?a="b"') == '<a href="/?a=&quot;b&quot;">x</a>'
    assert el("div", el("b", "kept")) == "<div><b>kept</b></div>"


def test_attribute_names_and_flags():
    assert el("input", type_="checkbox", data_k="vars-lt50k") == \
        '<input type="checkbox" data-k="vars-lt50k">'
    assert el("details", open=True) == "<details open></details>"
    # an absent attribute is absent, not empty
    assert el("a", "x", aria_current=None) == "<a>x</a>"
    assert el("a", "x", aria_current=False) == "<a>x</a>"


def test_void_elements_have_no_closing_tag():
    assert el("br") == "<br>"
    assert el("meta", charset="utf-8") == '<meta charset="utf-8">'


def test_join_escapes_what_is_not_markup():
    assert join(["<", Markup("<b>"), ">"]) == "&lt;<b>&gt;"


def test_fmt_escapes_every_substitution():
    assert fmt("<p>{x}</p>", x="<script>") == "<p>&lt;script&gt;</p>"
    assert fmt("<p>{x}</p>", x=Markup("<b>ok</b>")) == "<p><b>ok</b></p>"


def test_fmt_refuses_a_substitution_it_was_not_given():
    with pytest.raises(KeyError):
        fmt("<p>{x}</p>")


def test_a_facet_option_from_miplib_data_cannot_inject_markup(index):
    """The fixed facets are literals, but the structure group is built from
    MIPLIB's tags, which are external data. Before the escaping boundary both
    the label and the `data-k` key went to the page raw."""
    from website import load as L

    samples = L.load_index(index)
    rows = [s for s in samples if s.subset == "primal"]
    hostile = ('<img src=x onerror=alert(1)>', 'tag-"><script>', lambda _s: True)
    rail = B._facet_rail([("Structure (MIPLIB)", [hostile])], rows)
    assert "<img" not in rail
    assert "<script>" not in rail
    assert "&lt;img src=x onerror=alert(1)&gt;" in rail
    assert 'data-k="tag-&quot;&gt;&lt;script&gt;"' in rail
