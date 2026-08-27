import re

from website import assets as A

TOKENS = ["--paper", "--raise", "--ink", "--muted", "--rule", "--rule-soft",
          "--primal", "--primal-wash", "--dual", "--dual-wash"]


def _root_block(css):
    m = re.search(r":root\{(.*?)\}", css, re.S)
    return m.group(1)


def test_every_token_is_defined_on_bare_root():
    block = _root_block(A.STYLESHEET)
    for t in TOKENS:
        assert f"{t}:" in block, f"{t} missing from bare :root"


def test_each_colour_is_defined_once_and_carries_both_schemes():
    """The dark palette used to be written out twice, under prefers-color-scheme
    and under [data-theme="dark"], with the light one repeated in the guard
    between them: three places to keep in step for every colour on the site."""
    block = _root_block(A.STYLESHEET)
    for t in TOKENS:
        assert A.STYLESHEET.count(f"{t}:") == 1, f"{t} is defined more than once"
        light_dark = re.search(rf"{re.escape(t)}:light-dark\(([^)]*)\)", block)
        assert light_dark, f"{t} names no dark value"
        light, dark = (v.strip() for v in light_dark.group(1).split(","))
        assert light and dark and light != dark, f"{t}: {light} / {dark}"


def test_a_manual_theme_switches_the_scheme_rather_than_the_palette():
    """What a toggle would set. Two lines, because light-dark() resolves against
    the used colour scheme rather than against a second copy of the colours."""
    assert "color-scheme:light dark" in A.STYLESHEET
    assert ':root[data-theme="light"]{color-scheme:light}' in A.STYLESHEET
    assert ':root[data-theme="dark"]{color-scheme:dark}' in A.STYLESHEET


def test_the_sticky_offsets_are_measured_from_the_bar_they_clear():
    """56 and 78 were four literals derived from one height."""
    assert "--topbar-h:56px" in A.STYLESHEET
    assert "height:var(--topbar-h)" in A.STYLESHEET
    assert "top:var(--topbar-h)" in A.STYLESHEET
    assert A.STYLESHEET.count("top:calc(var(--topbar-h) + 22px)") == 2
    assert "78px" not in A.STYLESHEET


def test_body_paints_its_own_background():
    # anchored to a line start, so a rule like `html,body{...}` earlier in the
    # sheet is not mistaken for the body rule itself
    m = re.search(r"^body\{(.*?)\}", A.STYLESHEET, re.S | re.M)
    assert m and "background:var(--paper)" in m.group(1)


def test_no_em_dash_anywhere_in_assets():
    for text in (A.STYLESHEET, A.SITE_JS, A.font_face()):
        assert "—" not in text and "&mdash;" not in text


def test_the_disclosure_script_only_opens_and_closes_the_rail():
    assert "http" not in A.DISCLOSURE_SCRIPT
    assert f"matchMedia('(max-width: {A.COMPACT_WIDTH}px)')" in A.SITE_JS
    assert "facets.open = !compact" in A.DISCLOSURE_SCRIPT
    # what the rail contains is the table script's business, not this one's
    assert "data-k" not in A.DISCLOSURE_SCRIPT
    assert "result-count" not in A.DISCLOSURE_SCRIPT


def test_the_browse_script_reads_the_page_rather_than_the_markup():
    """It evaluates the facet declaration the page ships. The bucket a row falls
    in used to be decided by the build and written onto the row as data-f."""
    assert "http" not in A.BROWSE_SCRIPT
    assert "browse-data" in A.BROWSE_SCRIPT
    assert "data-f" not in A.BROWSE_SCRIPT
    assert "bucket.kind === 'term'" in A.BROWSE_SCRIPT
    assert "bucket.lo" in A.BROWSE_SCRIPT and "bucket.hi" in A.BROWSE_SCRIPT
    assert "data-k" in A.BROWSE_SCRIPT          # which bucket a checkbox selects
    assert "button[data-sort]" in A.BROWSE_SCRIPT
    assert "keydown" not in A.BROWSE_SCRIPT     # a native button supplies it
    assert "result-count" in A.BROWSE_SCRIPT
    assert "table-foot" not in A.BROWSE_SCRIPT


def test_a_filtered_view_has_an_address():
    """A filtered, sorted table is worth sending to someone, and a reload used
    to lose it. replaceState, so Back leaves the page rather than undoing a
    checkbox at a time."""
    assert "URLSearchParams" in A.BROWSE_SCRIPT
    assert "location.search" in A.BROWSE_SCRIPT
    assert "history.replaceState" in A.BROWSE_SCRIPT
    assert "pushState" not in A.BROWSE_SCRIPT
    assert "params.set('sort'" in A.BROWSE_SCRIPT


def test_the_browse_script_never_renders_a_row():
    """One renderer, in Python. This moves and hides the elements it was given."""
    for creating in ("createElement", "innerHTML", "insertAdjacentHTML"):
        assert creating not in A.BROWSE_SCRIPT


def test_mobile_layout_has_explicit_overflow_guards():
    assert "grid-template-columns:196px minmax(0,1fr)" in A.STYLESHEET
    assert ".detail{display:grid;grid-template-columns:minmax(0,1fr) 292px" in A.STYLESHEET
    assert ".detail-head h1" in A.STYLESHEET and "overflow-wrap:anywhere" in A.STYLESHEET
    assert ".btn-label{min-width:0;overflow-wrap:anywhere}" in A.STYLESHEET
    assert "thead th{position:static}" in A.STYLESHEET
    assert "height:auto;min-height:var(--topbar-h)" in A.STYLESHEET
    # the two subset names do not fit six equal cells on a phone
    assert ".nav-short{display:none}" in A.STYLESHEET
    assert "nav.top .nav-full{display:none}" in A.STYLESHEET
    assert "nav.top .nav-short{display:inline}" in A.STYLESHEET
    # 200% zoom on common desktop widths produces a 640-720px CSS viewport.
    assert f"@media (max-width:{A.COMPACT_WIDTH}px)" in A.SITE_CSS
    assert ".topbar{position:static}" in A.STYLESHEET


def test_topbar_fallback_and_button_size_text_keep_their_contrast():
    topbar = re.search(r"\.topbar\{(.*?)\}", A.STYLESHEET, re.S).group(1)
    assert topbar.index("background:var(--paper)") < topbar.index("background:color-mix")
    size = re.search(r"\.btn \.sz\{(.*?)\}", A.STYLESHEET, re.S).group(1)
    assert "opacity" not in size


def test_the_compact_breakpoint_is_one_number():
    """A media query cannot read a custom property, so the stylesheet and the
    script each carried 780 with nothing keeping the two in step."""
    assert f"@media (max-width:{A.COMPACT_WIDTH}px)" in A.SITE_CSS
    assert f"matchMedia('(max-width: {A.COMPACT_WIDTH}px)')" in A.SITE_JS
    assert "COMPACT_PX" not in A.SITE_CSS and "COMPACT_PX" not in A.SITE_JS


def test_the_script_targets_the_browsers_the_stylesheet_does():
    """light-dark(), color-mix() and overflow:clip put the floor at 2024. The
    script was written against 2018: var, Array.prototype.forEach.call on a
    NodeList, and a MediaQueryList.addListener fallback for Safari 13."""
    assert "var " not in A.SITE_JS
    assert "Array.prototype" not in A.SITE_JS
    assert ".addListener(" not in A.SITE_JS


def test_the_page_loads_nothing_from_a_third_party():
    """The fonts are served from the site, so an archived copy renders as published
    and a reader is not announced to a font CDN."""
    assert "http" not in A.font_face()
    for family, style, weight in A.FONT_FACES:
        assert f"fonts/IBMPlex{family}-{style}.woff2" in A.font_face()
        assert f"font-weight:{weight}" in A.font_face()


def test_font_paths_are_relative_to_the_page_that_carries_them():
    """The stylesheet is inlined into pages at three different depths, so a path
    that worked at the root would 404 two levels down."""
    assert "url(fonts/IBMPlexSans-Regular.woff2)" in A.font_face()
    assert "url(../../fonts/IBMPlexSans-Regular.woff2)" in A.font_face("../../")


def test_the_shipped_faces_cover_the_glyphs_the_pages_set():
    """The arrows and inequalities are outside the Latin subset a CDN serves, and
    they appear in the branch recipe on every primal page."""
    import pathlib
    names = {p.name for p in (pathlib.Path(__file__).parents[1]
                              / "fonts").glob("*.woff2")}
    for family, style, _ in A.FONT_FACES:
        assert f"IBMPlex{family}-{style}.woff2" in names
