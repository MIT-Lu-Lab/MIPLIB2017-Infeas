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
    """Click-only sorting is unreachable for keyboard and screen-reader users."""
    html = _browse(index, "primal")
    heads = re.findall(r"<th[^>]*data-sort=[^>]*>", html)
    assert heads
    for h in heads:
        assert 'tabindex="0"' in h, h
        assert 'role="button"' in h, h
        assert "aria-label=" in h, h


def test_tags_that_are_false_of_an_lp_are_not_offered(index):
    """The published files are continuous LPs: a tag naming a variable type is
    false of them, and MIPLIB's benchmark-set membership is about MIPLIB."""
    html = _browse(index, "primal")
    for tag in ("mixed_binary", "binary", "integer_knapsack",
                "benchmark_suitable", "feasibility"):
        assert f'data-k="tag-{tag}"' not in html, tag
