from dataclasses import replace

from tests.htmlq import page
from website import render as V
from website.domain import BSD_LICENSED_SOURCE, DualProvenance, Sample
from website.index import load_collection


def _render(sample, cross=None, *args, **kwargs):
    """A page rendered with the one instance it is about.

    These tests are about what a page says, not about the cloud it draws, so
    the collection they hand it is that instance alone.
    """
    return V.render_sample(sample, cross, *args, samples=[sample], **kwargs)


def _samples(index):
    return {(sample.subset, sample.instance): sample for sample in load_collection(index)}


def test_primal_page_shows_the_branch_recipe(index):
    s = _samples(index)[("primal", "bbb")]
    html = _render(s, None)
    # the fixture records no column name, so the index is labelled as one
    assert "column 1 ≥ 2" in html  # this instance's own side
    assert "column 1 ≤ 1" in html  # the side the search took


def test_primal_page_uses_the_resolved_column_name(index):
    """A 0-based index printed as a name invents one, and on 23 published
    instances collides with a real column of that name."""
    s = _samples(index)[("primal", "bbb")]
    named = replace(s, provenance=replace(s.primal, branch_var_name="make_widget_7"))
    html = _render(named, None)
    assert "make_widget_7 ≥ 2" in html
    assert "column 1 ≥ 2" not in html


def test_primal_page_truncates_the_bound_path(index):
    s = _samples(index)[("primal", "bbb")]
    html = _render(s, None)
    assert "1 of 1 shown" in html


def test_dual_page_lists_drops_and_counts(index):
    s = _samples(index)[("dual", "aaa")]
    html = _render(s, None)
    assert "Bounds dropped" in html and "Rows dropped" in html
    assert "c0" in html


def test_cross_link_appears_only_when_the_pair_exists(index):
    m = _samples(index)
    with_cross = _render(m[("primal", "aaa")], m[("dual", "aaa")])
    without = _render(m[("primal", "bbb")], None)
    # the shared stylesheet defines ".crosslink" CSS rules on every page, so the bare
    # word appears regardless; check for the actual element instead.
    assert page(with_cross).one("a.crosslink")
    assert not page(without).all("a.crosslink")


def test_cross_link_is_coloured_by_the_half_it_points_at(index):
    """The accent names its target. Fixed to the dual colour it said "dual" on a
    dual page, where the link goes the other way."""
    m = _samples(index)
    # the link is toned for the half it points at, not the one it sits on
    from_primal = page(_render(m[("primal", "aaa")], m[("dual", "aaa")]))
    from_dual = page(_render(m[("dual", "aaa")], m[("primal", "aaa")]))
    assert "d" in from_primal.one("a.crosslink").classes
    assert "p" in from_dual.one("a.crosslink").classes


def test_cross_link_href_matches_page_path(index):
    m = _samples(index)
    html = _render(m[("primal", "aaa")], m[("dual", "aaa")])
    assert f'href="../../{m[("dual", "aaa")].page_path}"' in html


def test_source_instance_card_links_to_miplib(index):
    s = _samples(index)[("primal", "aaa")]
    html = _render(s, None)
    assert "https://miplib.zib.de/instance_details_aaa.html" in html


def test_download_button_is_disabled_without_a_url(index):
    s = _samples(index)[("primal", "aaa")]
    buttons = page(_render(s, None)).all("span.btn")
    assert buttons, "the button is still shown, as a placeholder"
    assert all(button.get("aria-disabled") == "true" for button in buttons)
    assert buttons[0].one("span.btn-label").text == "aaa_if.mps.gz"


def test_download_button_is_enabled_with_a_url(index):
    s = _samples(index)[("primal", "aaa")]
    root = page(_render(s, None, release_base_url="https://e.invalid"))
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
    html = _render(s, None)
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
    html = _render(credited, None)
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

    licensed = _render(s, None)
    assert "CC BY-SA 4.0" in licensed
    assert "No licence of record" not in licensed

    legacy = _render(replace(s, imported_from="Imported from MIPLIB2010."), None)
    assert "No licence of record" in legacy
    assert "CC BY-SA 4.0" not in legacy
    # MIPLIB's own wording is the evidence, so it is quoted rather than paraphrased
    assert "Imported from MIPLIB2010." in legacy
    assert 'href="../../LICENSE.txt"' in legacy


def test_the_one_bsd_source_is_not_shown_as_cc_by_sa(index):
    """Its contributor chose other terms; ZIB records `other-license: BSD`."""
    s = _samples(index)[("primal", "aaa")]
    bsd = _render(replace(s, instance=BSD_LICENSED_SOURCE), None)
    assert "BSD 3-Clause" in bsd
    assert "CC BY-SA 4.0" not in bsd


def test_source_card_omits_absent_metadata(index):
    """The cache is optional; without it the page still renders."""
    s = _samples(index)[("primal", "aaa")]
    html = _render(s, None)
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
    html = _render(described, None)
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
    html = _render(s, None)
    assert "1 entry" in html and "1 entries" not in html


def test_a_primal_page_states_the_work_as_well_as_the_place(index):
    """Depth says where the node sits; it does not say how much searching
    found it. Two nodes at the same depth can come from runs orders of
    magnitude apart."""
    sample = replace(_samples(index)[("primal", "aaa")], search_nodes=8_421)
    text = " ".join(page(_render(sample)).all("dl.kv")[1].text.split())
    # the run first, then where in it this node sits
    assert text.index("Nodes the run processed 8,421") < text.index("Depth in the tree")
    assert f"Depth in the tree {sample.primal.depth}" in text


def test_a_primal_page_omits_a_node_count_it_was_not_given(index):
    """The count comes from the miners' log, not the published file."""
    assert "Nodes the run" not in _render(_samples(index)[("primal", "aaa")])


def test_a_dual_page_separates_what_was_tried_from_what_was_kept(index):
    """The greedy search removes far more than it leaves, and the two numbers
    are the whole point of calling the result inclusion-minimal."""
    sample = _samples(index)[("dual", "aaa")]
    # the first list is the instance's own dimensions; the provenance is next
    text = " ".join(page(_render(sample)).all("dl.kv")[1].text.split())
    assert f"Rounds run {sample.dual.rounds}" in text
    assert f"Bounds dropped {sample.dual.bounds_dropped}" in text
    assert f"Rows dropped {sample.dual.rows_dropped}" in text


def test_a_dual_page_omits_rounds_the_sidecar_did_not_record(index):
    """Absent is not zero: the published schema does not require n_rounds."""
    sample = _samples(index)[("dual", "aaa")]
    silent = replace(sample, provenance=replace(sample.dual, rounds=None))
    assert "Rounds run" not in _render(silent)


def test_the_page_points_at_its_own_nonzero_pattern(index):
    """One raster per instance, named for the file it describes. It is a mask,
    so the card would be a solid square if the URL missed."""
    sample = _samples(index)[("primal", "aaa")]
    node = page(_render(sample, None)).one("div.pattern")
    assert f"url('../../patterns/{sample.stem}.png')" in node.get("style")
    assert sample.instance in node.get("aria-label")
    assert node.get("role") == "img"


def test_detail_page_labels_breadcrumb_and_sidebar(index):
    root = page(_render(_samples(index)[("primal", "aaa")], None))
    assert root.one("nav.crumb").get("aria-label") == "Breadcrumb"
    aside = root.one("aside.aside")
    assert aside.get("aria-label") == "Context, downloads and source"
    # each card in it is headed, so the two are distinguishable in a list of
    # landmarks rather than being two unnamed boxes
    assert [h.text for h in aside.all("h2.eyebrow")] == [
        "Nonzero entries",
        "Where it sits",
        "Download",
        "Source instance",
    ]
