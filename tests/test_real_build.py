"""The whole published collection, built from the committed index.

This used to need the 2.3 GB of published files and so only ever ran on a machine
that had them. The index carries what the pages render, so these now run anywhere
the repository is checked out, CI included.
"""

import re
from pathlib import Path

import pytest

from website import build_site as B

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "metadata" / "site-index.json"
MIPLIB = ROOT / "metadata" / "miplib_meta.json"

pytestmark = pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    B.build(INDEX, out, miplib_path=MIPLIB)
    return out


def test_page_count_matches_the_collection(built):
    pages = list(built.rglob("index.html"))
    # 334 instance pages + 2 browse + overview + guide + download + about
    assert len(pages) == 340


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
    assert "229 have no feasible point" in text
    assert "other 105 are unbounded" in text
    assert "up to 20,682,487 variables and 19,912,111 constraints" in text


def test_every_instance_page_credits_its_miplib_submitter(built):
    """CC BY-SA requires adapted material to identify the original's creator, and
    the index carries no submitters: they come from the MIPLIB metadata."""
    pages = [p for p in built.rglob("index.html")
             if p.parent.parent.name.endswith("-infeasible")]
    assert len(pages) == 334
    credited = sum("Submitted by" in p.read_text(encoding="utf-8") for p in pages)
    assert credited > 300, f"only {credited}/334 pages name a submitter"
