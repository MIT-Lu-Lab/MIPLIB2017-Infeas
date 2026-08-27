from website import load as L, records as R, render as V


def test_download_page_links_the_archives_and_indexes(index):
    samples = L.load_index(index)
    html = V.render_download(L.collection_totals(samples),
                             release_base_url="https://e.invalid/dl")
    assert 'href="https://e.invalid/dl/primal-infeasible.zip"' in html
    assert 'href="https://e.invalid/dl/dual-infeasible.zip"' in html
    assert 'href="../primal-infeasible.csv"' in html
    assert 'href="../dual-infeasible.csv"' in html
    assert "manifest_infeas.csv" not in html and "manifest_unbnd.csv" not in html
    assert "primal-infeasible.urls.txt" not in html


def test_download_archive_links_disabled_without_a_release(index):
    samples = L.load_index(index)
    html = V.render_download(L.collection_totals(samples))
    assert 'aria-disabled="true"' in html
    assert "https://" not in html.split('<main')[1].split('</main>')[0]


def test_download_page_states_no_size_when_it_has_none(index):
    """Without the per-subset sizes the page must omit the figure, not sum an empty
    mapping to "0 B" and state it as fact."""
    samples = L.load_index(index)
    totals = L.collection_totals(samples)
    assert "0 B" not in V.render_download(totals)
    assert "in all" not in V.render_download(totals)
    sizes = L.subset_bytes(samples)
    assert f"{R.fmt_bytes(sum(sizes.values()))} in all" in V.render_download(totals, sizes=sizes)


def test_download_page_does_not_mention_zenodo(index):
    samples = L.load_index(index)
    html = V.render_download(L.collection_totals(samples))
    # Zenodo was dropped: its 100-file cap cannot hold a 668-file release
    assert "Zenodo" not in html and "zenodo" not in html
    # both archives are named, since they are the entry point for the whole set
    assert "primal-infeasible.zip" in html and "dual-infeasible.zip" in html


def test_overview_citation_carries_no_doi(index):
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples))
    assert "doi" not in html.lower()
    assert "howpublished" in html


def test_overview_citation_uses_the_supplied_site_url(index):
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples),
                             site_url="https://example.invalid/miplib-infeas")
    assert "https://example.invalid/miplib-infeas" in html
    assert "REPLACE-WITH" not in html


def test_about_credits_miplib_and_states_the_licence():
    html = V.render_about()
    assert "MIPLIB 2017" in html
    assert "CC BY-SA 4.0" in html
    # not plain CC-BY: the source instances are ShareAlike, so the adaptation must be too
    assert "CC-BY 4.0" not in html


def test_about_describes_both_mining_procedures():
    html = V.render_about()
    assert "branch-and-bound" in html
    assert "unbounded" in html


def test_static_pages_have_no_em_dash(index):
    samples = L.load_index(index)
    for html in (V.render_download(L.collection_totals(samples)), V.render_about()):
        assert "—" not in html and "&mdash;" not in html


def test_about_names_the_solver_that_produced_the_collection():
    html = V.render_about()
    # reproducing the tree requires knowing which solver built it
    assert "CPLEX" in html
    assert "HiGHS" in html and "Gurobi" in html
