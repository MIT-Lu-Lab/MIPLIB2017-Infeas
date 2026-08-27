"""What a search result and a shared link show.

A page with no description is a bare URL in a chat window and an untitled row in
a result list. For a collection that exists to be found and cited, that is most
of what a reader sees before deciding whether to open it.
"""

import re

from website import content, load as L, render as V


def _head(html: str) -> str:
    return html.split("</head>", 1)[0]


def _meta(html: str, key: str, attr: str = "name") -> str | None:
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', html)
    return m.group(1) if m else None


def test_every_page_type_carries_a_description(index):
    samples = L.load_index(index)
    totals = L.collection_totals(samples)
    pages = [
        V.render_overview(totals),
        V.render_browse("primal", samples),
        V.render_sample(samples[0], None),
        V.render_guide(),
        V.render_download(totals),
        V.render_about(),
    ]
    for html in pages:
        head = _head(html)
        description = _meta(head, "description")
        assert description, f"no description: {re.search(r'<title>(.*?)<', head)}"
        assert _meta(head, "og:description", attr="property") == description
        assert _meta(head, "og:title", attr="property")
        assert _meta(head, "og:site_name", attr="property") == content.NAME
        assert _meta(head, "twitter:card") == "summary"


def test_a_description_fits_what_a_result_shows(index):
    """Past about 160 characters a description is truncated, so its end is
    written for no one."""
    samples = L.load_index(index)
    totals = L.collection_totals(samples)
    longest = max(samples, key=lambda s: len(s.instance))
    pages = [V.render_overview(totals), V.render_browse("primal", samples),
             V.render_sample(longest, None), V.render_guide(),
             V.render_download(totals), V.render_about()]
    for html in pages:
        description = _meta(_head(html), "description") or ""
        assert len(description) <= content.META_LIMIT, description


def test_the_canonical_url_is_absent_until_the_build_knows_the_origin(index):
    """A guessed canonical points readers and crawlers at a URL that may not
    exist, which is worse than none."""
    samples = L.load_index(index)
    head = _head(V.render_sample(samples[0], None))
    assert "canonical" not in head
    assert 'property="og:url"' not in head

    url = "https://example.invalid/mi/primal-infeasible/aaa/"
    head = _head(V.render_sample(samples[0], None, url))
    assert f'<link rel="canonical" href="{url}">' in head
    assert _meta(head, "og:url", attr="property") == url


def test_the_description_of_an_instance_leads_with_its_name(index):
    """A search result and a shared link are both read name-first."""
    samples = L.load_index(index)
    s = next(x for x in samples if x.subset == "primal")
    description = _meta(_head(V.render_sample(s, None)), "description")
    assert description.startswith(s.instance)


def test_a_description_is_escaped_for_its_attribute():
    hostile = 'x" onload="alert(1)'
    html = V.page("t", V.Markup(""), active="about", depth=0, description=hostile)
    assert 'onload=' not in _head(html).replace('content="x&quot; onload=&quot;', "")
    assert "&quot; onload=&quot;alert(1)" in html
