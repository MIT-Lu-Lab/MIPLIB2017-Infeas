import json
import re

from website import load as L, render as V


def _browse(index, subset):
    samples = L.load_index(index)
    return V.render_browse(subset, samples)


def payload(html: str) -> dict:
    """What the page ships for the client to filter and sort by."""
    m = re.search(r'<script id="browse-data" type="application/json">(.*?)</script>',
                  html, re.S)
    assert m, "the page ships no browse data"
    return json.loads(m.group(1).replace(r"<\/", "</"))


def test_primal_table_lists_only_primal_rows(index):
    html = _browse(index, "primal")
    assert len(payload(html)["rows"]) == 2
    assert ">aaa<" in html and ">bbb<" in html


def test_dual_table_has_the_relaxation_columns(index):
    html = _browse(index, "dual")
    assert "Bounds dropped" in html and "Rows dropped" in html
    assert "Depth" not in html


def test_primal_table_has_depth_and_bound_changes(index):
    html = _browse(index, "primal")
    assert "Depth" in html and "Bounds tightened" in html
    assert "Bounds dropped" not in html


def test_the_payload_describes_the_rendered_rows_in_order(index):
    """The client pairs the two by position and then only hides and moves the
    elements the build produced, so the order is the contract between them."""
    html = _browse(index, "primal")
    body = re.search(r"<tbody>(.*?)</tbody>", html, re.S).group(1)
    rendered = re.findall(r'<th scope="row" class="name"><a href="[^"]*">([^<]*)<', body)
    assert rendered == [row["instance"] for row in payload(html)["rows"]]


def test_a_row_ships_the_values_it_is_filtered_and_sorted_by(index):
    row = next(r for r in payload(_browse(index, "primal"))["rows"]
               if r["instance"] == "bbb")
    assert row["n_vars"] == 10
    assert set(row) >= {"n_vars", "n_cons", "nnz", "file_bytes", "depth", "tags"}


def test_a_row_carries_no_derived_filter_token(index):
    """The bucket a row falls in is a conclusion about a value the page already
    ships. It used to be computed at build time and written onto every row."""
    for subset in ("primal", "dual"):
        assert "data-f=" not in _browse(index, subset)


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


def test_every_checkbox_is_selectable_from_the_payload(index):
    """A checkbox the client cannot resolve to a bucket filters nothing."""
    for subset in ("primal", "dual"):
        html = _browse(index, subset)
        selectable = {f"{facet['param']}-{bucket['value']}"
                      for facet in payload(html)["facets"]
                      for bucket in facet["buckets"]}
        offered = set(re.findall(r'data-k="([^"]+)"', html))
        assert offered == selectable


def test_every_sortable_header_names_a_field_a_row_carries(index):
    for subset in ("primal", "dual"):
        html = _browse(index, subset)
        carried = set(payload(html)["rows"][0])
        for field in re.findall(r'data-sort="([^"]+)"', html):
            assert field in carried, field


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


def test_the_search_field_is_labelled_and_waits_for_its_script(index):
    """A field that does nothing is worse than none, so the markup ships it
    hidden and the script that makes it work is what reveals it."""
    html = _browse(index, "primal")
    assert '<div class="table-search" hidden>' in html
    assert ('<label class="sr-only" for="instance-search">'
            "Search instances by name</label>") in html
    assert 'type="search" id="instance-search"' in html


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
    assert '<th scope="row" class="name"><a href="aaa/">aaa</a></th>' in html


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
