from dataclasses import replace

from website import load as L, records as R, render as V


def _samples(index):
    return {(s.subset, s.instance): s for s in L.load_index(index)}


def test_primal_page_shows_the_branch_recipe(index):
    s = _samples(index)[("primal", "bbb")]
    html = V.render_sample(s, None)
    # the fixture records no column name, so the index is labelled as one
    assert "column 1 ≥ 2" in html    # this instance's own side
    assert "column 1 ≤ 1" in html    # the side the search took


def test_primal_page_uses_the_resolved_column_name(index):
    """A 0-based index printed as a name invents one, and on 23 published
    instances collides with a real column of that name."""
    s = _samples(index)[("primal", "bbb")]
    named = replace(s, provenance=replace(s.primal, branch_var_name="make_widget_7"))
    html = V.render_sample(named, None)
    assert "make_widget_7 ≥ 2" in html
    assert "column 1 ≥ 2" not in html


def test_primal_page_says_column_when_no_name_is_recorded(index):
    s = _samples(index)[("primal", "bbb")]
    html = V.render_sample(s, None)   # fixture carries no branch_var_name
    assert "column 1" in html


def test_primal_page_truncates_the_bound_path(index):
    s = _samples(index)[("primal", "bbb")]
    html = V.render_sample(s, None)
    assert "1 of 1 shown" in html


def test_dual_page_lists_drops_and_counts(index):
    s = _samples(index)[("dual", "aaa")]
    html = V.render_sample(s, None)
    assert "Bounds dropped" in html and "Rows dropped" in html
    assert "c0" in html


def test_cross_link_appears_only_when_the_pair_exists(index):
    m = _samples(index)
    with_cross = V.render_sample(m[("primal", "aaa")], m[("dual", "aaa")])
    without = V.render_sample(m[("primal", "bbb")], None)
    # the shared stylesheet defines ".crosslink" CSS rules on every page, so the bare
    # word appears regardless; check for the actual element instead.
    # a primal page links to the dual half, so the link wears the dual accent
    assert 'class="crosslink d"' in with_cross
    assert 'class="crosslink' not in without


def test_cross_link_is_coloured_by_the_half_it_points_at(index):
    """The accent names its target. Fixed to the dual colour it said "dual" on a
    dual page, where the link goes the other way."""
    m = _samples(index)
    assert 'class="crosslink d"' in V.render_sample(m[("primal", "aaa")], m[("dual", "aaa")])
    assert 'class="crosslink p"' in V.render_sample(m[("dual", "aaa")], m[("primal", "aaa")])


def test_cross_link_href_matches_page_path(index):
    m = _samples(index)
    html = V.render_sample(m[("primal", "aaa")], m[("dual", "aaa")])
    assert f'href="../../{m[("dual", "aaa")].page_path}"' in html


def test_source_instance_card_links_to_miplib(index):
    s = _samples(index)[("primal", "aaa")]
    html = V.render_sample(s, None)
    assert "https://miplib.zib.de/instance_details_aaa.html" in html


def test_download_button_is_disabled_without_a_url(index):
    s = _samples(index)[("primal", "aaa")]
    html = V.render_sample(s, None)
    assert 'aria-disabled="true"' in html
    assert '<span class="btn-label">aaa_if.mps.gz</span>' in html


def test_download_button_is_enabled_with_a_url(index):
    s = replace(_samples(index)[("primal", "aaa")],
                mps_url="https://e.invalid/aaa_if.mps.gz",
                meta_url="https://e.invalid/aaa_if.meta.json")
    html = V.render_sample(s, None)
    assert 'href="https://e.invalid/aaa_if.mps.gz"' in html
    assert 'href="https://e.invalid/aaa_if.meta.json"' in html
    assert 'aria-disabled="true"' not in html
    assert html.count('class="btn-label"') == 2


def test_cut_fields_never_appear(index):
    s = _samples(index)[("dual", "aaa")]
    html = V.render_sample(s, None)
    for cut in ("parent_uid", "parent_depth", "schema_version", "sample_kind",
                "beta", "n_rounds", "picks", "sample_id"):
        assert cut not in html


def test_no_em_dash(index):
    s = _samples(index)[("primal", "bbb")]
    assert "—" not in V.render_sample(s, None)


def test_dual_page_natural_unbounded_has_accurate_copy():
    s = R.Sample(instance="ddd", n_vars=3, n_cons=2, nnz=4,
                 file_bytes=100, meta_bytes=10,
                 provenance=R.DualProvenance(bounds_dropped=0, rows_dropped=0,
                                             natural_unbounded=True))
    html = V.render_sample(s, None)
    assert ("The source instance's LP relaxation is unbounded as given. Nothing was "
            "removed to produce this instance.") in html
    assert "0 of 0 shown" not in html
    assert "What was removed" not in html


def test_source_card_credits_the_miplib_submitter(index):
    """CC BY-SA requires adapted material to identify the original's creator."""
    s = _samples(index)[("primal", "aaa")]
    credited = R.Sample(**{**s.__dict__, "submitter": "A. Contributor",
                           "tags": ("set_partitioning", "numerics"),
                           "source_description": "A scheduling model."})
    html = V.render_sample(credited, None)
    assert "A. Contributor" in html
    assert "set_partitioning" in html and "numerics" in html
    assert "A scheduling model." in html
    # MIPLIB's prose must be labelled as theirs, not passed off as ours
    assert "Source description quoted from MIPLIB 2017" in html


def test_source_card_omits_absent_metadata(index):
    """The cache is optional; without it the page still renders."""
    s = _samples(index)[("primal", "aaa")]
    html = V.render_sample(s, None)
    assert "Submitted by" not in html
    assert "Source description quoted from MIPLIB" not in html
    assert "miplib.zib.de/instance_details_aaa.html" in html


def test_source_description_formats_links_and_known_math_safely(index):
    s = _samples(index)[("primal", "aaa")]
    described = replace(
        s, source_description=("See https://example.test/model. Its matrix is "
                               r"\(n\times n\); <b>upstream text</b>."))
    html = V.render_sample(described, None)
    assert '<a href="https://example.test/model">https://example.test/model</a>.' in html
    assert "n \N{MULTIPLICATION SIGN} n" in html and r"\(n\times n\)" not in html
    assert "&lt;b&gt;upstream text&lt;/b&gt;" in html


def test_one_removed_element_uses_the_singular():
    drop = {"kind": "bound", "side": "lb", "var": 0, "name": "x"}
    s = R.Sample(instance="one-drop", n_vars=1, n_cons=1, nnz=1,
                 file_bytes=1, meta_bytes=1,
                 provenance=R.DualProvenance(
                     bounds_dropped=1, rows_dropped=0, drops_head=(drop,)))
    html = V.render_sample(s, None)
    assert "1 entry" in html and "1 entries" not in html


def test_detail_page_labels_breadcrumb_and_sidebar(index):
    html = V.render_sample(_samples(index)[("primal", "aaa")], None)
    assert '<nav class="crumb" aria-label="Breadcrumb">' in html
    assert '<aside class="aside" aria-label="Downloads and source">' in html
    assert '<h2 class="eyebrow">Download</h2>' in html
    assert '<h2 class="eyebrow">Source instance</h2>' in html
