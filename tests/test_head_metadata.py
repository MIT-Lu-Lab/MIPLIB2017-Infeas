"""What a search result and a shared link show.

A page with no description is a bare URL in a chat window and an untitled row in
a result list. For a collection that exists to be found and cited, that is most
of what a reader sees before deciding whether to open it.
"""

from tests.htmlq import page
from website import assets as A
from website import content
from website import render as V
from website.domain import collection_totals, subset_bytes
from website.index import load_collection


def _render(sample, cross=None, *args, **kwargs):
    """A page rendered with the one instance it is about.

    These tests are about what a page says, not about the cloud it draws, so
    the collection they hand it is that instance alone.
    """
    return V.render_sample(sample, cross, *args, samples=[sample], **kwargs)


def _head(html: str) -> str:
    return html.split("</head>", 1)[0]


def _meta(html: str, key: str, attr: str = "name") -> str | None:
    """A meta tag's content, found by what it names rather than by how the
    attributes happen to be ordered."""
    for tag in page(html).all("meta"):
        if tag.get(attr) == key:
            return tag.get("content")
    return None


def test_every_page_type_carries_a_description(index):
    samples = load_collection(index)
    totals = collection_totals(samples)
    sizes = subset_bytes(samples)
    pages = [
        V.render_overview(samples),
        V.render_browse("primal", samples),
        _render(samples[0], None),
        V.render_guide(130),
        V.render_download(totals, sizes),
        V.render_about(),
    ]
    for html in pages:
        head = _head(html)
        description = _meta(head, "description")
        assert description, f"no description on {page(head).one('title').text!r}"
        assert _meta(head, "og:description", attr="property") == description
        assert _meta(head, "og:title", attr="property")
        assert _meta(head, "og:site_name", attr="property") == content.NAME
        assert _meta(head, "twitter:card") == "summary"


def test_a_description_fits_what_a_result_shows(index):
    """Past about 160 characters a description is truncated, so its end is
    written for no one."""
    samples = load_collection(index)
    totals = collection_totals(samples)
    sizes = subset_bytes(samples)
    longest = max(samples, key=lambda s: len(s.instance))
    pages = [
        V.render_overview(samples),
        V.render_browse("primal", samples),
        _render(longest, None),
        V.render_guide(130),
        V.render_download(totals, sizes),
        V.render_about(),
    ]
    for html in pages:
        description = _meta(_head(html), "description") or ""
        assert len(description) <= content.META_LIMIT, description


def test_the_canonical_url_is_absent_until_the_build_knows_the_origin(index):
    """A guessed canonical points readers and crawlers at a URL that may not
    exist, which is worse than none."""
    samples = load_collection(index)
    head = _head(_render(samples[0], None))
    assert "canonical" not in head
    assert 'property="og:url"' not in head

    site = "https://example.invalid/mi/"
    head = _head(_render(samples[0], None, site))
    url = site + samples[0].page_path
    assert page(head).one('link[rel="canonical"]').get("href") == url
    assert _meta(head, "og:url", attr="property") == url


def test_the_card_a_shared_link_shows(index):
    """Slack, X and the rest draw og:image above the title. Without one, a link
    to a published dataset looks like a pasted URL."""
    samples = load_collection(index)

    head = _head(V.render_overview(samples))
    assert "og:image" not in head
    assert _meta(head, "twitter:card") == "summary"

    head = _head(V.render_overview(samples, site_url="https://example.invalid/mi/"))
    assert _meta(head, "og:image", attr="property") == "https://example.invalid/mi/og.png"
    width, height = A.OG_IMAGE_SIZE
    assert _meta(head, "og:image:width", attr="property") == str(width)
    assert _meta(head, "og:image:height", attr="property") == str(height)
    assert _meta(head, "og:image:alt", attr="property")
    # a picture is what makes it the large card rather than the thin one
    assert _meta(head, "twitter:card") == "summary_large_image"


def test_the_committed_card_is_a_png_of_the_declared_shape():
    """The size is declared in the head so a platform need not fetch the image
    to lay the card out. If the two disagree the card is drawn wrong."""
    import struct
    from pathlib import Path

    data = (Path(__file__).parents[1] / A.OG_IMAGE).read_bytes()
    # the signature, written as hex so the escape survives an editor
    assert data[:8] == bytes.fromhex("89504e470d0a1a0a")
    width, height = struct.unpack(">II", data[16:24])
    declared_width, declared_height = A.OG_IMAGE_SIZE
    assert width % declared_width == 0 and height % declared_height == 0
    assert width // declared_width == height // declared_height


def test_the_description_of_an_instance_leads_with_its_name(index):
    """A search result and a shared link are both read name-first."""
    samples = load_collection(index)
    s = next(x for x in samples if x.subset == "primal")
    description = _meta(_head(_render(s, None)), "description")
    assert description.startswith(s.instance)


def test_a_description_is_escaped_for_its_attribute(shell):
    hostile = 'x" onload="alert(1)'
    html = shell("t", active="about", page_rel="index.html", description=hostile)
    description = page(_head(html)).one('meta[name="description"]')
    assert description.get("content") == hostile
    assert description.get("onload") is None
