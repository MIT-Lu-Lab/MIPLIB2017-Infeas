from dataclasses import replace

from tests.htmlq import page
from website import render as V
from website.domain import BSD_LICENSED_SOURCE, DualProvenance, Sample
from website.index import load_collection


def _samples(index):
    return {(sample.subset, sample.instance): sample for sample in load_collection(index)}


def test_primal_page_shows_the_branch_recipe(index):
    s = _samples(index)[("primal", "bbb")]
    html = V.render_sample(s, None)
    # the fixture records no column name, so the index is labelled as one
    assert "column 1 ≥ 2" in html  # this instance's own side
    assert "column 1 ≤ 1" in html  # the side the search took


def test_primal_page_uses_the_resolved_column_name(index):
    """A 0-based index printed as a name invents one, and on 23 published
    instances collides with a real column of that name."""
    s = _samples(index)[("primal", "bbb")]
    named = replace(s, provenance=replace(s.primal, branch_var_name="make_widget_7"))
    html = V.render_sample(named, None)
    assert "make_widget_7 ≥ 2" in html
    assert "column 1 ≥ 2" not in html


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
    assert page(with_cross).one("a.crosslink")
    assert not page(without).all("a.crosslink")


def test_cross_link_is_coloured_by_the_half_it_points_at(index):
    """The accent names its target. Fixed to the dual colour it said "dual" on a
    dual page, where the link goes the other way."""
    m = _samples(index)
    # the link is toned for the half it points at, not the one it sits on
    from_primal = page(V.render_sample(m[("primal", "aaa")], m[("dual", "aaa")]))
    from_dual = page(V.render_sample(m[("dual", "aaa")], m[("primal", "aaa")]))
    assert "d" in from_primal.one("a.crosslink").classes
    assert "p" in from_dual.one("a.crosslink").classes


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
    buttons = page(V.render_sample(s, None)).all("span.btn")
    assert buttons, "the button is still shown, as a placeholder"
    assert all(button.get("aria-disabled") == "true" for button in buttons)
    assert buttons[0].one("span.btn-label").text == "aaa_if.mps.gz"


def test_download_button_is_enabled_with_a_url(index):
    s = _samples(index)[("primal", "aaa")]
    root = page(V.render_sample(s, None, release_base_url="https://e.invalid"))
    links = root.all("a.btn")
    assert [link.get("href") for link in links] == [
        "https://e.invalid/aaa_if.mps.gz",
        "https://e.invalid/aaa_if.meta.json",
    ]
    assert [link.one("span.btn-label").text for link in links] == [
        "aaa_if.mps.gz",
        "aaa_if.meta.json",
    ]
    assert not root.all("span.btn"), "nothing is a placeholder once it has a URL"


def test_dual_page_natural_unbounded_has_accurate_copy():
    s = Sample(
        instance="ddd",
        n_vars=3,
        n_cons=2,
        nnz=4,
        file_bytes=100,
        meta_bytes=10,
        provenance=DualProvenance(bounds_dropped=0, rows_dropped=0, natural_unbounded=True),
    )
    html = V.render_sample(s, None)
    assert (
        "The source instance's LP relaxation is unbounded as given. Nothing was "
        "removed to produce this instance."
    ) in html
    assert "0 of 0 shown" not in html
    assert "What was removed" not in html


def test_source_card_credits_the_miplib_submitter(index):
    """CC BY-SA requires adapted material to identify the original's creator."""
    s = _samples(index)[("primal", "aaa")]
    credited = replace(
        s,
        submitter="A. Contributor",
        tags=("set_partitioning", "numerics"),
        source_description="A scheduling model.",
    )
    html = V.render_sample(credited, None)
    assert "A. Contributor" in html
    assert "set_partitioning" in html and "numerics" in html
    assert "A scheduling model." in html
    # MIPLIB's prose must be labelled as theirs, not passed off as ours
    assert "Source description quoted from MIPLIB 2017" in html


def test_source_card_states_the_terms_of_this_instance_alone(index):
    """The 262 sources do not share one licence, so a page cannot imply they do.

    130 of them predate MIPLIB's submission form and carry no licence at all. A
    page that showed CC BY-SA beside one of those would assert a grant nobody
    made, which is the error this row exists to prevent.
    """
    s = _samples(index)[("primal", "aaa")]

    licensed = V.render_sample(s, None)
    assert "CC BY-SA 4.0" in licensed
    assert "No licence of record" not in licensed

    legacy = V.render_sample(replace(s, imported_from="Imported from MIPLIB2010."), None)
    assert "No licence of record" in legacy
    assert "CC BY-SA 4.0" not in legacy
    # MIPLIB's own wording is the evidence, so it is quoted rather than paraphrased
    assert "Imported from MIPLIB2010." in legacy
    assert 'href="../../LICENSE.txt"' in legacy


def test_the_one_bsd_source_is_not_shown_as_cc_by_sa(index):
    """Its contributor chose other terms; ZIB records `other-license: BSD`."""
    s = _samples(index)[("primal", "aaa")]
    bsd = V.render_sample(replace(s, instance=BSD_LICENSED_SOURCE), None)
    assert "BSD 3-Clause" in bsd
    assert "CC BY-SA 4.0" not in bsd


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
        s,
        source_description=(
            "See https://example.test/model. Its matrix is "
            r"\(n\times n\); <b>upstream text</b>."
        ),
    )
    html = V.render_sample(described, None)
    assert '<a href="https://example.test/model">https://example.test/model</a>.' in html
    assert "n \N{MULTIPLICATION SIGN} n" in html and r"\(n\times n\)" not in html
    assert "&lt;b&gt;upstream text&lt;/b&gt;" in html


def test_one_removed_element_uses_the_singular():
    drop = {"kind": "bound", "side": "lb", "var": 0, "name": "x"}
    s = Sample(
        instance="one-drop",
        n_vars=1,
        n_cons=1,
        nnz=1,
        file_bytes=1,
        meta_bytes=1,
        provenance=DualProvenance(bounds_dropped=1, rows_dropped=0, drops_head=(drop,)),
    )
    html = V.render_sample(s, None)
    assert "1 entry" in html and "1 entries" not in html


def test_detail_page_labels_breadcrumb_and_sidebar(index):
    root = page(V.render_sample(_samples(index)[("primal", "aaa")], None))
    assert root.one("nav.crumb").get("aria-label") == "Breadcrumb"
    aside = root.one("aside.aside")
    assert aside.get("aria-label") == "Context, downloads and source"
    # each card in it is headed, so the two are distinguishable in a list of
    # landmarks rather than being two unnamed boxes
    assert [h.text for h in aside.all("h2.eyebrow")] == [
        "Where it sits",
        "Download",
        "Source instance",
    ]
