import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from website import build as B
from website.index import SiteIndexError, load_collection

ROOT = Path(__file__).resolve().parents[1]


def test_build_writes_the_expected_tree(tmp_path, index):
    out = tmp_path / "out"
    n = B.build(index, out)
    for rel in (
        "index.html",
        "primal-infeasible/index.html",
        "primal-infeasible/aaa/index.html",
        "primal-infeasible/bbb/index.html",
        "dual-infeasible/index.html",
        "dual-infeasible/aaa/index.html",
        "download/index.html",
        "about/index.html",
        "guide/index.html",
        "LICENSE.txt",
        "og.png",
        "schema/meta.schema.json",
        "schema/sidecar/1.0.0/meta.schema.json",
        "schema/sidecar/1.0.1/meta.schema.json",
        "schema/sidecar/1.1.0/meta.schema.json",
        "schema/release-manifest/1.0.0/manifest.schema.json",
        ".nojekyll",
        "site-build.json",
    ):
        assert (out / rel).is_file(), rel
    assert n == 9


def test_build_publishes_the_canonical_sidecar_schema(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)

    published = out / "schema" / "meta.schema.json"
    assert published.read_bytes() == (ROOT / "schema/meta.schema.json").read_bytes()
    schema = json.loads(published.read_text(encoding="utf-8"))
    assert schema["$id"] == "https://mit-lu-lab.github.io/MIPLIB2017-Infeas/schema/meta.schema.json"

    versioned = out / "schema" / "sidecar" / "1.0.0" / "meta.schema.json"
    assert versioned.read_bytes() == (ROOT / "schema/sidecar/1.0.0/meta.schema.json").read_bytes()
    assert json.loads(versioned.read_text(encoding="utf-8"))["$id"].endswith(
        "/schema/sidecar/1.0.0/meta.schema.json"
    )


def test_build_publishes_the_licence_linked_from_about(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)
    assert (out / "LICENSE.txt").read_bytes() == (ROOT / "LICENSE").read_bytes()


def test_build_fails_loudly_when_the_index_is_missing(tmp_path):
    with pytest.raises(SiteIndexError):
        B.build(tmp_path / "nothing", tmp_path / "out")


def test_manifest_csvs_have_one_row_per_sample_of_that_subset(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)
    expected = {
        (sample.subset, sample.instance): (sample.sha256, sample.file_bytes)
        for sample in load_collection(index)
    }

    with (out / "primal-infeasible.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["instance"] for r in rows] == ["aaa", "bbb"]
    assert list(rows[0].keys()) == [
        "instance",
        "n_vars",
        "n_cons",
        "nnz",
        "depth",
        "bound_changes",
        "file_bytes",
        "sha256",
        "mps_filename",
    ]
    for r in rows:
        assert r["mps_filename"] == r["instance"] + "_if.mps.gz"
        assert (r["sha256"], int(r["file_bytes"])) == expected[("primal", r["instance"])]

    with (out / "dual-infeasible.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["instance"] for r in rows] == ["aaa"]
    assert list(rows[0].keys()) == [
        "instance",
        "n_vars",
        "n_cons",
        "nnz",
        "bounds_dropped",
        "rows_dropped",
        "file_bytes",
        "sha256",
        "mps_filename",
    ]
    for r in rows:
        assert r["mps_filename"] == r["instance"] + "_ub.mps.gz"
        assert (r["sha256"], int(r["file_bytes"])) == expected[("dual", r["instance"])]


def _assert_all_links_resolve(built):
    """Resolve every non-external href on every generated page under `built`."""
    for page in built.rglob("index.html"):
        base = page.parent
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]*)"', text):
            if href.startswith(("http", "#", "mailto:")):
                continue
            target = (base / href).resolve()
            if target.is_dir():
                target = target / "index.html"
            assert target.exists(), f"{page}: dead link {href!r}"


def test_every_internal_link_resolves(tmp_path, index):
    """The tmp fixture builds all eight page types (depth 0, 1 and 2), so this walker
    catches a `page()` depth constant that has drifted from where build() writes the
    page -- the kind of break unit tests on individual renderers do not see."""
    out = tmp_path / "out"
    B.build(index, out)
    _assert_all_links_resolve(out)


def test_release_base_url_produces_live_download_links(index, tmp_path):
    out = tmp_path / "out"
    B.build(index, out, release_base_url="https://e.invalid/dl")
    html = (out / "primal-infeasible/aaa/index.html").read_text(encoding="utf-8")
    assert 'href="https://e.invalid/dl/aaa_if.mps.gz"' in html
    assert 'href="https://e.invalid/dl/aaa_if.meta.json"' in html
    assert 'aria-disabled="true"' not in html


def test_release_base_url_must_be_absolute(index, tmp_path):
    """A prefix without a scheme would make every download link relative and dead,
    silently, across 670 assets."""
    with pytest.raises(ValueError) as exc:
        B.build(
            index, tmp_path / "out", release_base_url="github.com/org/repo/releases/download/v1.0"
        )
    message = str(exc.value)
    assert "absolute" in message and "github.com/org/repo" in message


def test_rebuild_is_deterministic_and_drops_unplanned_files(index, tmp_path):
    out = tmp_path / "out"
    B.build(index, out)
    first = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in out.rglob("*")
        if path.is_file()
    }
    (out / "stale.txt").write_text("stale", encoding="utf-8")

    B.build(index, out)
    second = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in out.rglob("*")
        if path.is_file()
    }
    assert second == first


def test_sitemap_is_public_only_and_uses_canonical_page_urls(index, tmp_path):
    out = tmp_path / "out"
    base = "https://example.test/MIPLIB2017-Infeas/"
    B.build(index, out, site_url=base[:-1])

    root = ET.parse(out / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in root.findall("sm:url/sm:loc", ns)]
    assert urls == sorted(
        {
            base,
            base + "about/",
            base + "download/",
            base + "dual-infeasible/",
            base + "dual-infeasible/aaa/",
            base + "guide/",
            base + "primal-infeasible/",
            base + "primal-infeasible/aaa/",
            base + "primal-infeasible/bbb/",
        }
    )

    B.build(index, out)
    assert not (out / "sitemap.xml").exists()


@pytest.mark.parametrize(
    "site_url",
    [
        "example.test/MIPLIB2017-Infeas",
        "ftp://example.test/MIPLIB2017-Infeas",
        "https:///MIPLIB2017-Infeas",
        "https://example.test/MIPLIB2017-Infeas?preview=1",
        "https://user:secret@example.test/MIPLIB2017-Infeas",
        "https://[bad/MIPLIB2017-Infeas",
        "https://:443/MIPLIB2017-Infeas",
        "https://example.test\\evil/MIPLIB2017-Infeas",
        "https://example.test/MI\x00PLIB-Infeas",
    ],
)
def test_site_url_must_be_a_clean_absolute_http_url(index, tmp_path, site_url):
    with pytest.raises(ValueError, match="site URL"):
        B.build(index, tmp_path / "out", site_url=site_url)


def test_the_whole_asset_chain_resolves_from_a_deep_page(index, tmp_path):
    """A build has to produce a site that renders on its own. The chain is three
    links long now: a page at depth 2 names the stylesheet, and the stylesheet
    names eight font files, each relative to itself rather than to the page."""
    out = tmp_path / "out"
    B.build(index, out)
    page = out / "primal-infeasible" / "aaa" / "index.html"
    hrefs = re.findall(r'(?:href|src)="([^"]*assets/[^"]+)"', page.read_text(encoding="utf-8"))
    assert len(hrefs) == 2, hrefs
    css = next(p for p in (page.parent / h for h in hrefs) if p.suffix == ".css")
    assert css.resolve().is_file()
    fonts = re.findall(r"url\(([^)]+)\)", css.read_text(encoding="utf-8"))
    assert len(fonts) == 8
    for rel in fonts:
        assert (css.parent / rel).resolve().is_file(), rel
    assert (out / "fonts" / "LICENSE.txt").is_file()
