import csv
import json
import re

import pytest

from website import build_site as B


def test_build_writes_the_expected_tree(tmp_path, index):
    out = tmp_path / "out"
    n = B.build(index, out)
    for rel in ("index.html",
                "primal-infeasible/index.html",
                "primal-infeasible/aaa/index.html",
                "primal-infeasible/bbb/index.html",
                "dual-infeasible/index.html",
                "dual-infeasible/aaa/index.html",
                "download/index.html",
                "about/index.html",
                "guide/index.html",
                "schema/meta.schema.json"):
        assert (out / rel).is_file(), rel
    assert n == 9


def test_relative_links_resolve_from_a_sample_page(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)
    html = (out / "primal-infeasible/aaa/index.html").read_text(encoding="utf-8")
    assert 'href="../../primal-infeasible/"' in html
    assert 'href="../../dual-infeasible/aaa/"' in html


def test_rebuild_is_idempotent(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)
    first = (out / "index.html").read_text(encoding="utf-8")
    B.build(index, out)
    assert (out / "index.html").read_text(encoding="utf-8") == first


def test_build_publishes_the_canonical_sidecar_schema(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)

    published = out / "schema" / "meta.schema.json"
    assert published.read_bytes() == B.SCHEMA_FILE.read_bytes()
    schema = json.loads(published.read_text(encoding="utf-8"))
    assert schema["$id"] == \
        "https://mit-lu-lab.github.io/MIPLIB-Infeas/schema/meta.schema.json"


def test_build_fails_loudly_when_the_index_is_missing(tmp_path):
    with pytest.raises(SystemExit):
        B.build(tmp_path / "nothing", tmp_path / "out")


def test_rebuild_prunes_stale_pages_but_keeps_other_files(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)

    ghost = out / "primal-infeasible" / "ghost" / "index.html"
    ghost.parent.mkdir(parents=True, exist_ok=True)
    ghost.write_text("stale", encoding="utf-8")
    nojekyll = out / ".nojekyll"
    nojekyll.write_text("", encoding="utf-8")

    B.build(index, out)

    assert not ghost.exists()
    assert not ghost.parent.exists()
    assert nojekyll.is_file()
    for rel in ("index.html",
                "primal-infeasible/index.html",
                "primal-infeasible/aaa/index.html",
                "primal-infeasible/bbb/index.html",
                "dual-infeasible/index.html",
                "dual-infeasible/aaa/index.html",
                "download/index.html",
                "about/index.html",
                "guide/index.html"):
        assert (out / rel).is_file(), rel
    # _prune only deletes stale index.html files; the published-set CSVs must survive.
    assert (out / "primal-infeasible.csv").is_file()
    assert (out / "dual-infeasible.csv").is_file()


def test_manifest_csvs_have_one_row_per_sample_of_that_subset(tmp_path, index):
    out = tmp_path / "out"
    B.build(index, out)

    with (out / "primal-infeasible.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["instance"] for r in rows] == ["aaa", "bbb"]
    assert list(rows[0].keys()) == [
        "instance", "n_vars", "n_cons", "nnz", "depth", "bound_changes",
        "file_bytes", "sha256", "mps_filename"]
    for r in rows:
        assert r["mps_filename"] == r["instance"] + "_if.mps.gz"

    with (out / "dual-infeasible.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["instance"] for r in rows] == ["aaa"]
    assert list(rows[0].keys()) == [
        "instance", "n_vars", "n_cons", "nnz", "bounds_dropped", "rows_dropped",
        "file_bytes", "sha256", "mps_filename"]
    for r in rows:
        assert r["mps_filename"] == r["instance"] + "_ub.mps.gz"


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


def test_release_urls_derives_every_filename_from_one_base(index):
    from website import load as L
    samples = L.load_index(index)
    urls = B.release_urls(samples, "https://github.com/org/repo/releases/download/v1.0/")
    # two entries per sample, and the trailing slash on the base is not doubled
    assert len(urls) == 2 * len(samples)
    assert urls["aaa_ub.mps.gz"] == \
        "https://github.com/org/repo/releases/download/v1.0/aaa_ub.mps.gz"
    assert urls["bbb_if.meta.json"] == \
        "https://github.com/org/repo/releases/download/v1.0/bbb_if.meta.json"


def test_release_base_url_produces_live_download_links(index, tmp_path):
    out = tmp_path / "out"
    B.build(index, out, release_base_url="https://e.invalid/dl")
    html = (out / "primal-infeasible/aaa/index.html").read_text(encoding="utf-8")
    assert 'href="https://e.invalid/dl/aaa_if.mps.gz"' in html
    assert 'href="https://e.invalid/dl/aaa_if.meta.json"' in html
    assert 'aria-disabled="true"' not in html


def test_prune_leaves_the_csv_indexes_alone(index, tmp_path):
    out = tmp_path / "out"
    B.build(index, out, release_base_url="https://e.invalid/dl")
    B.build(index, out, release_base_url="https://e.invalid/dl")
    for name in ("primal-infeasible.csv", "dual-infeasible.csv"):
        assert (out / name).is_file(), name


def test_csv_publishes_the_checksum_the_index_carries(index, tmp_path):
    """A byte count catches a truncated download; only a hash catches a corrupt one.
    The build never sees the published files, so the CSV can only be as good as the
    index, and scripts/build_site_index.py is what measures them."""
    import csv as _csv

    from website import load as L
    out = tmp_path / "out"
    B.build(index, out)
    want = {s.instance: (s.sha256, s.file_bytes)
            for s in L.load_index(index) if s.subset == "primal"}
    rows = list(_csv.DictReader((out / "primal-infeasible.csv").open(encoding="utf-8")))
    assert rows, "no rows to check"
    for r in rows:
        assert (r["sha256"], int(r["file_bytes"])) == want[r["instance"]]


def test_release_base_url_must_be_absolute(index, tmp_path):
    """A prefix without a scheme would make every download link relative and dead,
    silently, across 670 assets."""
    import pytest
    with pytest.raises(SystemExit) as exc:
        B.build(index, tmp_path / "out",
                release_base_url="github.com/org/repo/releases/download/v1.0")
    assert "absolute URL" in str(exc.value)


def test_prune_removes_a_stale_index_but_keeps_foreign_files(index, tmp_path):
    """The pruner owns what the build writes and nothing else: a Pages branch also
    carries CNAME, .nojekyll and the licence."""
    out = tmp_path / "out"
    B.build(index, out)
    (out / "primal-infeasible" / "ghost").mkdir(parents=True)
    (out / "primal-infeasible" / "ghost" / "index.html").write_text("stale", encoding="utf-8")
    (out / "stale-subset.csv").write_text("gone,soon\n", encoding="utf-8")
    (out / "fonts" / "IBMPlexDropped-Regular.woff2").write_bytes(b"wOF2stale")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "CNAME").write_text("example.invalid\n", encoding="utf-8")

    B.build(index, out)
    assert not (out / "primal-infeasible" / "ghost").exists()
    assert not (out / "stale-subset.csv").exists()
    assert not (out / "fonts" / "IBMPlexDropped-Regular.woff2").exists()
    assert (out / ".nojekyll").exists() and (out / "CNAME").exists()
    assert (out / "primal-infeasible.csv").exists()
    assert (out / "index.html").exists()


def test_build_emits_nojekyll(index, tmp_path):
    """Pages runs Jekyll unless told not to, and Jekyll drops any path starting
    with an underscore. The site deploys from a fresh artifact, so nothing carries
    the file across; the build has to put it there."""
    out = tmp_path / "out"
    B.build(index, out)
    assert (out / ".nojekyll").is_file()


def test_the_whole_asset_chain_resolves_from_a_deep_page(index, tmp_path):
    """A build has to produce a site that renders on its own. The chain is three
    links long now: a page at depth 2 names the stylesheet, and the stylesheet
    names eight font files, each relative to itself rather than to the page."""
    out = tmp_path / "out"
    B.build(index, out)
    page = out / "primal-infeasible" / "aaa" / "index.html"
    hrefs = re.findall(r'(?:href|src)="([^"]*assets/[^"]+)"',
                       page.read_text(encoding="utf-8"))
    assert len(hrefs) == 2, hrefs
    css = next(p for p in (page.parent / h for h in hrefs) if p.suffix == ".css")
    assert css.resolve().is_file()
    fonts = re.findall(r"url\(([^)]+)\)", css.read_text(encoding="utf-8"))
    assert len(fonts) == 8
    for rel in fonts:
        assert (css.parent / rel).resolve().is_file(), rel
    assert (out / "fonts" / "LICENSE.txt").is_file()


def test_a_stale_hashed_asset_is_pruned(index, tmp_path):
    """The name carries a digest, so an edited stylesheet lands beside the old one
    rather than over it, and every past build's copy would accumulate forever."""
    out = tmp_path / "out"
    B.build(index, out)
    stale = out / "assets" / "site.000000000000.css"
    stale.write_text("/* last build */", encoding="utf-8")
    B.build(index, out)
    assert not stale.exists()
    assert len(list((out / "assets").iterdir())) == 2
