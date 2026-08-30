import re

import pytest
from jinja2 import UndefinedError

from tests.htmlq import page
from website import render as V
from website.content import NAME
from website.domain import collection_totals
from website.index import load_collection
from website.render.shell import page as render_page


def test_page_shell_has_lang_title_and_the_shared_assets(shell):
    from website.assets import CSS_NAME, JS_NAME

    html = shell(active="overview", page_rel="index.html")
    assert html.startswith("<!doctype html>")
    root = page(html)
    assert root.one("html").get("lang") == "en"
    assert root.one("title").text == f"Example · {NAME}"
    # the stylesheet and script are shared files, not bytes repeated on every page
    stylesheet = root.one('link[rel="stylesheet"]')
    assert stylesheet.get("href") == f"assets/{CSS_NAME}"
    script = root.one("script[src]")
    assert script.get("src") == f"assets/{JS_NAME}"
    assert script.has("defer"), "a blocking script would delay every page"
    assert "--primal:#3B4CC0" not in html


def test_page_shell_has_skip_link_and_landmarks(shell):
    html = shell(active="overview", page_rel="index.html", description="Example page")
    root = page(html)
    main = root.one("main")
    skip = root.one("a.skip-link")
    # the link is what makes the landmark reachable, so it has to name it
    assert skip.get("href") == f"#{main.get('id')}"
    assert skip.text == "Skip to main content"
    assert main.get("tabindex") == "-1", "a skipped-to landmark takes focus"
    assert root.one("header.topbar")
    assert root.one("nav.top").get("aria-label") == "Primary navigation"


def test_short_nav_labels_keep_the_full_accessible_name(shell):
    html = shell(active="overview", page_rel="index.html", description="Example page")
    assert 'aria-label="Primal-infeasible"' in html
    assert 'aria-label="Dual-infeasible"' in html


def test_page_shell_links_resolve_by_depth(shell):
    root = shell(active="overview", page_rel="index.html")
    deep = shell(
        active="overview",
        page_rel="dual-infeasible/aaa/index.html",
        licence_href="../../LICENSE.txt",
    )
    assert 'href="primal-infeasible/"' in root
    assert 'href="../../primal-infeasible/"' in deep
    # a link takes the direct route rather than going to the root and back
    own = shell(
        active="primal",
        page_rel="primal-infeasible/aaa/index.html",
        licence_href="../../LICENSE.txt",
    )
    assert 'href="../"' in own
    assert "../../primal-infeasible/" not in own


def test_active_nav_item_is_marked(shell):
    html = shell(active="dual", page_rel="index.html")
    # The current-page state belongs to the primary navigation only.
    nav = page(html).one("nav.top")
    current = [link for link in nav.all("a") if link.has("aria-current")]
    assert [link.text for link in current] == ["Dual-infeasible Dual"]


def test_only_the_long_nav_labels_carry_a_short_form(shell):
    """Both forms ship and the stylesheet hides one, so a name that outgrows a
    phone cell is shortened rather than overlapping its neighbour."""
    nav = page(shell(active="overview", page_rel="index.html")).one("nav.top")
    pairs = {
        link.one("span.nav-full").text: link.one("span.nav-short").text
        for link in nav.all("a")
        if link.all("span.nav-short")
    }
    assert pairs == {"Primal-infeasible": "Primal", "Dual-infeasible": "Dual"}
    # a name that fits keeps one label and no spans at all
    guide = next(link for link in nav.all("a") if link.text == "Guide")
    assert guide.children == []


def test_templates_fail_when_required_context_is_missing():
    with pytest.raises(UndefinedError):
        render_page("about.html", "A", active="about", page_rel="about/index.html")


def test_overview_reports_real_counts_and_ranges(index):
    samples = load_collection(index)
    html = V.render_overview(collection_totals(samples))
    text = " ".join(html.split())  # the prose wraps, so normalise whitespace
    assert "3 linear programs" in text  # total
    assert "2 have no feasible point; 1 is unbounded" in text
    assert "up to 10 variables and 4 constraints" in text


def test_overview_uses_the_public_instance_vocabulary(index):
    samples = load_collection(index)
    html = V.render_overview(collection_totals(samples))
    low = html.lower()
    # published items are called instances, the word this field uses; "sample" was the
    # mining pipeline's internal vocabulary and must not reach the page
    assert "instances" in low
    assert "sample" not in low


def test_overview_names_the_maintainers_and_authors(index):
    samples = load_collection(index)
    html = V.render_overview(collection_totals(samples))
    assert "Bo Tang" in html and "Haihao Lu" in html
    assert "MIT-Lu-Lab/MIPLIB2017-Infeas/issues" in html
    assert "author" in html  # the citation must be attributable


def test_overview_says_the_files_are_pure_lps(index):
    """Whether integrality survived decides which claims about these files hold."""
    samples = load_collection(index)
    text = " ".join(V.render_overview(collection_totals(samples)).split())
    assert "integrality dropped" in text


def test_overview_ships_the_figure_for_both_media(index):
    """One figure per medium, each with the same description.

    A reader who cannot see either one gets the alt text, and a reader printing
    the page gets the light figure rather than a black rectangle.
    """
    samples = load_collection(index)
    html = V.render_overview(collection_totals(samples))
    root = page(html).one("figure.figure")
    images = root.all("img")
    assert [image.get("class") for image in images] == ["on-screen", "on-paper"]
    assert [image.get("src") for image in images] == [
        "figures/size-scatter.svg",
        "figures/size-scatter-print.svg",
    ]
    assert all(image.get("alt") for image in images)
    assert root.one("figcaption").text


def test_overview_carries_a_machine_readable_dataset_description(index):
    """Dataset search engines read the JSON-LD and nothing else on the page.
    Without it the collection is a web page that happens to mention linear
    programs, and the people most likely to want it never find it."""
    import json

    html = V.render_overview(
        collection_totals(load_collection(index)),
        site_url="https://example.invalid/mi/",
        release_base_url="https://e.invalid/dl",
    )
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert m, "no JSON-LD on the overview"
    doc = json.loads(m.group(1))
    assert doc["@type"] == "Dataset"
    assert doc["url"] == "https://example.invalid/mi/"
    # No blanket "license": 131 source instances carry CC BY-SA 4.0, one carries
    # BSD 3-Clause and 130 carry none, so one machine-readable licence for the
    # dataset would assert a grant nobody made. Consumers get the notice instead.
    assert "license" not in doc
    assert doc["usageInfo"] == "https://example.invalid/mi/LICENSE.txt"
    assert {c["name"] for c in doc["creator"]} == {"Haihao Lu", "Bo Tang"}
    assert [d["contentUrl"] for d in doc["distribution"]] == [
        "https://e.invalid/dl/primal-infeasible.zip",
        "https://e.invalid/dl/dual-infeasible.zip",
    ]
    # the counts in it have to be the real ones, not a number typed into a template
    assert "3 linear programs" in doc["description"]


def test_the_dataset_description_points_at_the_notice_absolutely(index):
    """A dataset catalogue reads this document off-site, where a relative path
    resolves against nothing. Without an origin the field is absent rather than
    a guess, as the canonical URL is."""
    import json

    samples = load_collection(index)

    doc = json.loads(
        re.search(
            r'ld\+json">(.*?)</script>', V.render_overview(collection_totals(samples)), re.S
        ).group(1)
    )
    assert "usageInfo" not in doc

    doc = json.loads(
        re.search(
            r'ld\+json">(.*?)</script>',
            V.render_overview(collection_totals(samples), site_url="https://example.invalid/mi/"),
            re.S,
        ).group(1)
    )
    assert doc["usageInfo"] == "https://example.invalid/mi/LICENSE.txt"
    assert "license" not in doc


def test_the_dataset_description_omits_downloads_it_does_not_have(index):
    import json

    html = V.render_overview(collection_totals(load_collection(index)))
    doc = json.loads(re.search(r'ld\+json">(.*?)</script>', html, re.S).group(1))
    assert "distribution" not in doc
    assert "url" not in doc
