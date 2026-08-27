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

from website import build_site as B

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "metadata" / "site-index.json"
MIPLIB = ROOT / "metadata" / "miplib_meta.json"
PUBLIC_BASE = "https://example.test/MIPLIB-Infeas/"

pytestmark = pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    B.build(INDEX, out, miplib_path=MIPLIB, site_url=PUBLIC_BASE)
    return out


def test_page_count_matches_the_collection(built):
    pages = list(built.rglob("index.html"))
    # 334 instance pages + 2 browse + overview + guide + download + about
    assert len(pages) == 340


def test_published_schema_matches_the_repository_source(built):
    published = built / "schema" / "meta.schema.json"
    source = ROOT / "schema" / "meta.schema.json"
    assert published.read_bytes() == source.read_bytes()


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
        for tag in re.findall(r"<(?:script|img)[^>]*>", html):
            assert not re.search(r'src="https?://', tag), f"{where}: {tag}"
        for tag in re.findall(r"<link[^>]*>", html):
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
    for page in built.rglob("index.html"):
        base = page.parent
        for href in re.findall(r'href="([^"]+)"', page.read_text(encoding="utf-8")):
            if href.startswith(("http", "#", "mailto:")):
                continue
            target = (base / href).resolve()
            if target.is_dir():
                target = target / "index.html"
            assert target.exists(), f"{page}: dead link {href}"


def test_every_font_the_pages_ask_for_is_carried(built):
    for page in built.rglob("index.html"):
        base = page.parent
        for url in re.findall(r"url\(([^)]*fonts/[^)]+)\)",
                              page.read_text(encoding="utf-8")):
            assert (base / url).resolve().exists(), f"{page}: missing font {url}"


def test_overview_reports_the_real_totals(built):
    text = " ".join((built / "index.html").read_text(encoding="utf-8").split())
    assert "334 linear programs" in text
    assert "229 have no feasible point; 105 are unbounded" in text
    assert "up to 20,682,487 variables and 19,912,111 constraints" in text


def test_dual_copy_accounts_for_both_derivation_paths(built):
    pages = [built / "index.html", built / "dual-infeasible" / "index.html",
             built / "about" / "index.html"]
    text = " ".join(" ".join(p.read_text(encoding="utf-8").split()) for p in pages)
    assert "103" in text and "two" in text
    assert "inclusion-minimal" in text
    assert "unbounded as given" in text


def test_every_page_has_unique_discovery_metadata_matching_the_sitemap(built):
    titles, descriptions, canonicals = [], [], []
    for page in sorted(built.rglob("index.html")):
        html = page.read_text(encoding="utf-8")
        title = re.findall(r"<title>(.*?)</title>", html)
        description = re.findall(r'<meta name="description" content="([^"]+)">', html)
        canonical = re.findall(r'<link rel="canonical" href="([^"]+)">', html)
        assert len(title) == len(description) == len(canonical) == 1, page
        page_rel = page.relative_to(built).as_posix()
        assert canonical[0] == PUBLIC_BASE + page_rel.removesuffix("index.html")
        titles.extend(title)
        descriptions.extend(description)
        canonicals.extend(canonical)

    assert len(titles) == 340
    assert len(set(titles)) == len(set(descriptions)) == len(set(canonicals)) == 340

    root = ET.parse(built / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {node.text for node in root.findall("sm:url/sm:loc", ns)}
    assert sitemap_urls == set(canonicals)

    overview = (built / "index.html").read_text(encoding="utf-8")
    payload = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                        overview, re.S).group(1)
    assert json.loads(payload)["url"] == PUBLIC_BASE


def test_every_instance_page_credits_its_miplib_submitter(built):
    """CC BY-SA requires adapted material to identify the original's creator, and
    the index carries no submitters: they come from the MIPLIB metadata."""
    pages = [p for p in built.rglob("index.html")
             if p.parent.parent.name.endswith("-infeasible")]
    assert len(pages) == 334
    credited = sum("Submitted by" in p.read_text(encoding="utf-8") for p in pages)
    assert credited > 300, f"only {credited}/334 pages name a submitter"
