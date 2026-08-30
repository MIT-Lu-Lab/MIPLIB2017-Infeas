"""The whole published collection, built from the committed index.

This used to need the 2.3 GB of published files and so only ever ran on a machine
that had them. The index carries what the pages render, so these now run anywhere
the repository is checked out, CI included.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from website import build as B
from website.index import load_collection

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "metadata" / "site-index.json"
MIPLIB = ROOT / "metadata" / "miplib_meta.json"
PUBLIC_BASE = "https://example.test/MIPLIB2017-Infeas/"

pytestmark = pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    B.build(INDEX, out, miplib_path=MIPLIB, site_url=PUBLIC_BASE)
    return out


def test_page_count_matches_the_collection(built):
    pages = list(built.rglob("index.html"))
    # One detail page per instance, two browse pages and four static pages.
    assert len(pages) == len(load_collection(INDEX)) + 6


# A <link> fetches for rel=stylesheet, preload, icon and their kin; it does not
# for canonical and alternate, which name a URL rather than load one.
NON_FETCHING_LINK_RELS = frozenset({"canonical", "alternate"})


def test_no_page_fetches_anything_from_a_third_party(built):
    """A reader must not be announced to a third party to read a page.

    Links in the prose are the point of the site and are not what this looks at.
    The rule lived only in a CI grep, which is how adding a canonical URL, whose
    href is absolute by definition, turned every page into a failure of a check
    about fetching.
    """
    for page in built.rglob("index.html"):
        html = page.read_text(encoding="utf-8")
        where = page.relative_to(built)
        for tag in re.findall(r"<(?:script|img)\b[^>]*>", html):
            assert not re.search(r'src="https?://', tag), f"{where}: {tag}"
        for tag in re.findall(r"<link\b[^>]*>", html):
            if not re.search(r'href="https?://', tag):
                continue
            rel = re.search(r'rel="([^"]*)"', tag)
            assert rel and rel.group(1) in NON_FETCHING_LINK_RELS, f"{where}: {tag}"


def test_no_page_contains_an_em_dash(built):
    for page in built.rglob("index.html"):
        text = page.read_text(encoding="utf-8")
        assert "—" not in text, page
        assert "&mdash;" not in text, page


def test_no_page_mentions_a_size_class(built):
    for page in built.rglob("index.html"):
        text = page.read_text(encoding="utf-8")
        for word in (">Small<", ">Medium<", ">Large<"):
            assert word not in text, f"{page}: {word}"


def test_every_internal_link_resolves(built):
    """Both what a page links to and what it loads: a figure that did not ship
    is a broken image rather than a dead link, and nothing else would say so."""
    for page in built.rglob("index.html"):
        base = page.parent
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'(?:href|src)="([^"]+)"', text):
            if href.startswith(("http", "#", "mailto:")):
                continue
            target = (base / href).resolve()
            if target.is_dir():
                target = target / "index.html"
            assert target.exists(), f"{page}: dead link {href}"


def test_every_pattern_a_page_asks_for_was_published(built):
    """The pattern is reached from a style attribute, not an href, so the link
    check above walks straight past a missing one."""
    seen = 0
    for page in built.rglob("*/*/index.html"):
        for url in re.findall(r"mask-image:url\('([^']+)'\)", page.read_text(encoding="utf-8")):
            assert (page.parent / url).resolve().exists(), f"{page}: no pattern {url}"
            seen += 1
    # a page carries two, one prefixed for older engines; a rename of the
    # property would otherwise leave this finding nothing and passing
    assert seen == 2 * len(load_collection(INDEX))


def test_no_relative_url_hides_inside_a_custom_property(built):
    """A url() inside a custom property is resolved against the stylesheet that
    substitutes it, not against the page that declared it.

    Both resolve alike when the site is served from the root of a host, which
    is how it is served in development, so the pattern masks looked right here
    and loaded nothing once published under a directory.
    """
    from website import assets as A

    sources = [A.SITE_CSS] + [
        page.read_text(encoding="utf-8") for page in built.rglob("*/*/index.html")
    ]
    for text in sources:
        assert not re.search(r"--[a-z-]+\s*:\s*url\(", text)


def test_overview_reports_the_real_totals(built):
    text = " ".join((built / "index.html").read_text(encoding="utf-8").split())
    assert "334 linear programs" in text
    assert "229 have no feasible point; 105 are unbounded" in text
    assert "up to 20,682,487 variables and 19,912,111 constraints" in text


def test_dual_copy_accounts_for_both_derivation_paths(built):
    pages = [
        built / "index.html",
        built / "dual-infeasible" / "index.html",
        built / "about" / "index.html",
    ]
    text = " ".join(" ".join(p.read_text(encoding="utf-8").split()) for p in pages)
    assert "103" in text and "two" in text
    assert "inclusion-minimal" in text
    assert "unbounded as given" in text


def test_every_page_has_unique_discovery_metadata_matching_the_sitemap(built):
    titles, descriptions, canonicals = [], [], []
    for page in sorted(built.rglob("index.html")):
        # the head only: a drawing in the body carries a <title> of its own for
        # every dot it holds, and none of those is what a search result shows
        head = page.read_text(encoding="utf-8").split("</head>", 1)[0]
        title = re.findall(r"<title>(.*?)</title>", head)
        description = re.findall(r'<meta name="description" content="([^"]+)">', head)
        canonical = re.findall(r'<link rel="canonical" href="([^"]+)">', head)
        assert len(title) == len(description) == len(canonical) == 1, page
        page_rel = page.relative_to(built).as_posix()
        assert canonical[0] == PUBLIC_BASE + page_rel.removesuffix("index.html")
        titles.extend(title)
        descriptions.extend(description)
        canonicals.extend(canonical)

    assert len(set(titles)) == len(titles)
    assert len(set(descriptions)) == len(descriptions)
    assert len(set(canonicals)) == len(canonicals)

    root = ET.parse(built / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {node.text for node in root.findall("sm:url/sm:loc", ns)}
    assert sitemap_urls == set(canonicals)

    overview = (built / "index.html").read_text(encoding="utf-8")
    payload = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', overview, re.S
    ).group(1)
    assert json.loads(payload)["url"] == PUBLIC_BASE


def test_every_instance_page_credits_its_miplib_submitter(built):
    """CC BY-SA requires adapted material to identify the original's creator, and
    the index carries no submitters: they come from the MIPLIB metadata."""
    pages = [p for p in built.rglob("index.html") if p.parent.parent.name.endswith("-infeasible")]
    expected = len(load_collection(INDEX))
    assert len(pages) == expected
    credited = sum("Submitted by" in p.read_text(encoding="utf-8") for p in pages)
    assert credited / expected > 0.9, f"only {credited}/{expected} pages name a submitter"
