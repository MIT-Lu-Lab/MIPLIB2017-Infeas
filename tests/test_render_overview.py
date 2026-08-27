import re

from website import load as L, render as V


def test_page_shell_has_lang_title_and_the_shared_assets():
    from website.assets import CSS_NAME, JS_NAME
    html = V.page("Example", "<p>hi</p>", active="overview", page_rel="index.html")
    assert html.startswith("<!doctype html>")
    assert '<html lang="en">' in html
    assert "<title>Example</title>" in html
    # the stylesheet and the scripts are two files, not 18 KB repeated on 340 pages
    assert f'<link rel="stylesheet" href="assets/{CSS_NAME}">' in html
    assert f'<script src="assets/{JS_NAME}" defer></script>' in html
    assert "--primal:#3B4CC0" not in html


def test_page_shell_has_skip_link_and_landmarks():
    html = V.page("Example", V.Markup("<h1>Example</h1>"),
                  active="overview", page_rel="index.html", description="Example page")
    assert '<a class="skip-link" href="#main-content">Skip to main content</a>' in html
    assert '<header class="topbar">' in html and '</header>' in html
    assert '<nav class="top" aria-label="Primary navigation">' in html
    assert '<main id="main-content" tabindex="-1">' in html


def test_short_nav_labels_keep_the_full_accessible_name():
    html = V.page("Example", V.Markup(""), active="overview", page_rel="index.html",
                  description="Example page")
    assert 'aria-label="Primal-infeasible"' in html
    assert 'aria-label="Dual-infeasible"' in html


def test_page_shell_links_resolve_by_depth():
    root = V.page("A", "", active="overview", page_rel="index.html")
    deep = V.page("A", "", active="overview",
                  page_rel="dual-infeasible/aaa/index.html")
    assert 'href="primal-infeasible/"' in root
    assert 'href="../../primal-infeasible/"' in deep
    # a link takes the direct route rather than going to the root and back
    own = V.page("A", "", active="primal",
                 page_rel="primal-infeasible/aaa/index.html")
    assert 'href="../"' in own
    assert "../../primal-infeasible/" not in own


def test_active_nav_item_is_marked():
    html = V.page("A", "", active="dual", page_rel="index.html")
    # Scoped to <nav>: assets.STYLESHEET separately contains the literal
    # substring 'aria-current="page"' in a CSS attribute selector, which
    # would otherwise double-count against the whole page.
    nav_html = re.search(r"<nav [^>]*>(.*?)</nav>", html, re.S).group(1)
    assert 'aria-current="page"' in nav_html
    assert nav_html.count('aria-current="page"') == 1


def test_only_the_long_nav_labels_carry_a_short_form():
    """Both forms ship and the stylesheet hides one, so a name that outgrows a
    phone cell is shortened rather than overlapping its neighbour."""
    nav_html = re.search(r"<nav [^>]*>(.*?)</nav>",
                         V.page("A", "", active="overview", page_rel="index.html"), re.S).group(1)
    assert '<span class="nav-full">Primal-infeasible</span>' in nav_html
    assert '<span class="nav-short">Primal</span>' in nav_html
    assert '<span class="nav-short">Dual</span>' in nav_html
    assert nav_html.count('class="nav-short"') == 2
    assert ">Guide</a>" in nav_html      # a name that fits stays a bare label


def test_overview_reports_real_counts_and_ranges(index):
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples))
    text = " ".join(html.split())          # the prose wraps, so normalise whitespace
    assert "3 linear programs" in text     # total
    assert "2 have no feasible point; 1 is unbounded" in text
    assert "up to 10 variables and 4 constraints" in text


def test_overview_counts_instances_and_omits_size_class(index):
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples))
    low = html.lower()
    # published items are called instances, the word this field uses; "sample" was the
    # mining pipeline's internal vocabulary and must not reach the page
    assert "instances" in low
    assert "sample" not in low
    for word in ("small", "medium", "large"):
        assert f">{word}<" not in low


def test_no_em_dash_in_rendered_output(index):
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples))
    assert "—" not in html and "&mdash;" not in html


def test_esc_escapes_markup():
    assert V.esc('<a & "b">') == "&lt;a &amp; &quot;b&quot;&gt;"


def test_overview_markup_is_balanced(index):
    """A stray <div class="section"> once nested the citation inside an empty one."""
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples))
    assert html.count("<div") == html.count("</div>")


def test_overview_names_the_maintainers_and_authors(index):
    samples = L.load_index(index)
    html = V.render_overview(L.collection_totals(samples))
    assert "Bo Tang" in html and "Haihao Lu" in html
    assert "MIT-Lu-Lab/MIPLIB-Infeas/issues" in html
    assert "author" in html          # the citation must be attributable


def test_overview_says_the_files_are_pure_lps(index):
    """Whether integrality survived decides which claims about these files hold."""
    samples = L.load_index(index)
    text = " ".join(V.render_overview(L.collection_totals(samples)).split())
    assert "integrality dropped" in text


def test_overview_carries_a_machine_readable_dataset_description(index):
    """Dataset search engines read the JSON-LD and nothing else on the page.
    Without it the collection is a web page that happens to mention linear
    programs, and the people most likely to want it never find it."""
    import json
    import re
    html = V.render_overview(L.collection_totals(L.load_index(index)),
                             site_url="https://example.invalid/mi",
                             release_base_url="https://e.invalid/dl")
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert m, "no JSON-LD on the overview"
    doc = json.loads(m.group(1))
    assert doc["@type"] == "Dataset"
    assert doc["url"] == "https://example.invalid/mi"
    # No blanket "license": 141 source instances carry CC BY-SA 4.0, one carries
    # BSD 3-Clause and 120 carry none, so one machine-readable licence for the
    # dataset would assert a grant nobody made. Consumers get the notice instead.
    assert "license" not in doc
    assert doc["usageInfo"] == "LICENSE.txt"
    assert {c["name"] for c in doc["creator"]} == {"Haihao Lu", "Bo Tang"}
    assert [d["contentUrl"] for d in doc["distribution"]] == [
        "https://e.invalid/dl/primal-infeasible.zip",
        "https://e.invalid/dl/dual-infeasible.zip"]
    # the counts in it have to be the real ones, not a number typed into a template
    assert "3 linear programs" in doc["description"]


def test_the_dataset_description_omits_downloads_it_does_not_have(index):
    import json
    import re
    html = V.render_overview(L.collection_totals(L.load_index(index)))
    doc = json.loads(re.search(r'ld\+json">(.*?)</script>', html, re.S).group(1))
    assert "distribution" not in doc
    assert "url" not in doc
    assert "REPLACE-WITH" not in html
