import re

from website import load as L, render as V


def _browse(index, subset):
    samples = L.load_index(index)
    return V.render_browse(subset, samples)


def test_primal_table_lists_only_primal_rows(index):
    html = _browse(index, "primal")
    assert html.count('<tr data-f="') == 2
    assert ">aaa<" in html and ">bbb<" in html


def test_dual_table_has_the_relaxation_columns(index):
    html = _browse(index, "dual")
    assert "Bounds dropped" in html and "Rows dropped" in html
    assert "Depth" not in html


def test_primal_table_has_depth_and_bound_changes(index):
    html = _browse(index, "primal")
    assert "Depth" in html and "Bounds tightened" in html
    assert "Bounds dropped" not in html


def test_numeric_cells_carry_a_sort_value(index):
    html = _browse(index, "primal")
    assert 'data-v="10"' in html      # n_vars of bbb


def test_facet_counts_are_computed_not_hardcoded(index):
    html = _browse(index, "primal")
    # both fixture samples are tiny, so the "<50 K" bucket holds 2
    assert '<span class="n">2</span>' in html


def test_mobile_filters_use_a_native_disclosure(index):
    html = _browse(index, "primal")
    assert '<details class="facets" open>' in html
    assert '<summary><span>Filters</span>' in html
    assert 'class="facet-selected">None selected</span>' in html
    assert '<div class="facet-groups">' in html
    assert '<fieldset class="facet"><legend class="eyebrow">Variables</legend>' in html


def test_row_data_f_matches_facet_predicates(index):
    # cannot execute the client-side filter from pytest; this pins the markup contract
    # it depends on instead -- see FILTER_SCRIPT in website/assets.py.
    html = _browse(index, "primal")
    assert '<tr data-f="vars-lt50k cons-lt10k depth-lt50">' in html   # aaa: also dual
    assert '<tr data-f="vars-lt50k cons-lt10k depth-lt50">' in html        # bbb: primal only


def test_dual_row_data_f_matches_facet_predicates(index):
    html = _browse(index, "dual")
    assert '<tr data-f="vars-lt50k cons-lt10k relax-bounds-rows size-1-5">' in html


def test_facet_checkbox_data_k_matches_the_row_keys(index):
    html = _browse(index, "primal")
    for key in ("vars-lt50k", "vars-50k-500k", "vars-gt500k",
                "cons-lt10k", "cons-10k-100k", "cons-gt100k",
                "depth-lt50", "depth-50-250", "depth-gt250"):
        assert f'data-k="{key}"' in html


def test_dual_facet_checkbox_data_k_matches_the_row_keys(index):
    html = _browse(index, "dual")
    for key in ("relax-bounds-only", "relax-bounds-rows", "relax-natural",
                "size-1-5", "size-6-50", "size-gt50"):
        assert f'data-k="{key}"' in html


def test_no_size_class_and_no_em_dash(index):
    for subset in ("primal", "dual"):
        html = _browse(index, subset)
        assert "—" not in html
        for word in (">Small<", ">Medium<", ">Large<"):
            assert word not in html


def test_sortable_headers_are_keyboard_reachable(index):
    """Native buttons retain columnheader semantics and supply Enter/Space."""
    html = _browse(index, "primal")
    buttons = re.findall(r'<button[^>]*class="sort-button"[^>]*>', html)
    assert buttons
    for button in buttons:
        assert 'type="button"' in button, button
        assert "data-sort=" in button, button
        assert "aria-label=" in button, button
    assert '<th scope="col"><button' in html
    assert not re.search(r'<th[^>]+role="button"', html)


def test_table_has_headers_caption_and_a_named_scroll_region(index):
    html = _browse(index, "primal")
    assert ('class="table-wrap" tabindex="0" role="region" '
            'aria-labelledby="primal-infeasible-table-caption"') in html
    assert ('<caption id="primal-infeasible-table-caption" class="sr-only">'
            'Primal-infeasible instances</caption>') in html
    assert '<th scope="col">Download</th>' in html
    assert '<th scope="row" class="name" data-v="aaa">' in html


def test_download_names_and_filter_result_are_announced(index):
    html = _browse(index, "primal")
    assert 'aria-label="Download aaa as gzipped MPS: unavailable"' in html
    assert re.search(
        r'class="result-count" data-total="2"\s+role="status" '
        r'aria-live="polite" aria-atomic="true">2 instances\.</span>', html)
    assert "All data columns sort; Download does not." in html


def test_tags_that_are_false_of_an_lp_are_not_offered(index):
    """The published files are continuous LPs: a tag naming a variable type is
    false of them, and MIPLIB's benchmark-set membership is about MIPLIB."""
    html = _browse(index, "primal")
    for tag in ("mixed_binary", "binary", "integer_knapsack",
                "benchmark_suitable", "feasibility"):
        assert f'data-k="tag-{tag}"' not in html, tag
