import json
import re

from tests.htmlq import page
from website import render as V
from website.index import load_collection


def _browse(index, subset):
    samples = load_collection(index)
    return V.render_browse(subset, samples)


def payload(html: str) -> dict:
    """What the page ships for the client to filter and sort by."""
    m = re.search(r'<script id="browse-data" type="application/json">(.*?)</script>', html, re.S)
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
    assert rendered == [row["values"]["instance"] for row in payload(html)["rows"]]


def test_a_row_ships_only_the_values_the_browser_sorts_or_searches(index):
    row = next(
        r["values"]
        for r in payload(_browse(index, "primal"))["rows"]
        if r["values"]["instance"] == "bbb"
    )
    assert row["n_vars"] == 10
    assert set(row) == {
        "instance",
        "n_vars",
        "n_cons",
        "nnz",
        "depth",
        "bound_changes",
        "file_bytes",
    }


def test_a_row_carries_memberships_in_the_payload_not_the_markup(index):
    """Python is the only facet evaluator; the DOM carries no second token copy."""
    for subset in ("primal", "dual"):
        html = _browse(index, subset)
        assert "data-f=" not in html
        assert all(isinstance(row["matches"], list) for row in payload(html)["rows"])


def test_filters_are_a_native_disclosure_closed_until_enhanced(index):
    root = page(_browse(index, "primal"))
    rail = root.one("details.facets")
    assert not rail.has("open"), "inactive filters must not hide the no-JS table below"
    summary = rail.one("summary")
    assert summary.first("span").text == "Filters"
    assert summary.one("span.facet-selected").text == "None selected"
    assert rail.one("div.facet-groups")
    variables = rail.first("fieldset.facet")
    assert variables.get("data-param") == "vars"
    assert variables.one("legend").text == "Variables"


def test_every_checkbox_is_selectable_from_the_payload(index):
    """Every materialised membership resolves to an offered checkbox."""
    for subset in ("primal", "dual"):
        html = _browse(index, subset)
        offered = set(re.findall(r'data-k="([^"]+)"', html))
        carried = {key for row in payload(html)["rows"] for key in row["matches"]}
        assert carried <= offered
        assert carried


def test_every_sortable_header_names_a_field_a_row_carries(index):
    for subset in ("primal", "dual"):
        html = _browse(index, subset)
        carried = set(payload(html)["rows"][0]["values"])
        for field in re.findall(r'data-sort="([^"]+)"', html):
            assert field in carried, field


def test_the_search_field_is_labelled_and_waits_for_its_script(index):
    """A field that does nothing is worse than none, so the markup ships it
    hidden and the script that makes it work is what reveals it."""
    root = page(_browse(index, "primal"))
    box = root.one("div.table-search")
    assert box.has("hidden"), "a field that does nothing is worse than none"
    field = box.one("input")
    assert field.get("type") == "search" and field.get("id") == "instance-search"
    label = box.one("label")
    assert label.get("for") == field.get("id")
    assert label.text == "Search instances by name"
    assert all(checkbox.has("disabled") for checkbox in root.all("input[data-k]"))


def test_sortable_headers_are_keyboard_reachable(index):
    """Native buttons retain columnheader semantics and supply Enter/Space."""
    root = page(_browse(index, "primal"))
    buttons = root.all("button.sort-button")
    assert buttons
    for button in buttons:
        assert button.get("type") == "button"
        assert button.has("data-sort") and button.has("aria-label")
        assert button.has("disabled"), "it does nothing until the script runs"
        assert button.get("data-sort")
    for header in root.all("th"):
        # a button inside the header, not a role bolted onto the header, which
        # would take the columnheader semantics away from it
        assert header.get("role") is None
    assert root.first("th").one("button")


def test_table_has_headers_caption_and_a_named_scroll_region(index):
    root = page(_browse(index, "primal"))
    wrap = root.one("div.table-wrap")
    caption = root.one("caption")
    assert wrap.get("role") == "region" and wrap.get("tabindex") == "0"
    # the scroll region is named by the caption, so it is announced as one thing
    assert wrap.get("aria-labelledby") == caption.get("id")
    assert caption.text == "Primal-infeasible instances"
    assert [h.text for h in root.all("th[scope=col]")][-1] == "Download"
    first_row = root.one("tbody").first("tr")
    name = first_row.one("th.name")
    assert name.get("scope") == "row"
    assert name.one("a").get("href") == "aaa/" and name.text == "aaa"


def test_download_names_and_filter_result_are_announced(index):
    html = _browse(index, "primal")
    assert 'aria-label="Download aaa as gzipped MPS: unavailable"' in html
    assert re.search(
        r'class="result-count" role="status"\s+'
        r'aria-live="polite" aria-atomic="true">2 instances\.</span>',
        html,
    )
    note = page(html).one("span.sort-note")
    assert note.has("hidden")
    assert note.text == "All data columns sort; Download does not."


def test_tags_that_are_false_of_an_lp_are_not_offered(index):
    """The published files are continuous LPs: a tag naming a variable type is
    false of them, and MIPLIB's benchmark-set membership is about MIPLIB."""
    html = _browse(index, "primal")
    for tag in ("mixed_binary", "binary", "integer_knapsack", "benchmark_suitable", "feasibility"):
        assert f'data-k="tag-{tag}"' not in html, tag
