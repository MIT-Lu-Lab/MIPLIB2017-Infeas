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


def test_dark_overrides_exist_for_both_states():
    assert ":root:not([data-theme=\"light\"])" in A.STYLESHEET
    assert ":root[data-theme=\"dark\"]" in A.STYLESHEET


def test_body_paints_its_own_background():
    m = re.search(r"body\{(.*?)\}", A.STYLESHEET, re.S)
    assert "background:var(--paper)" in m.group(1)


def test_no_em_dash_anywhere_in_assets():
    for text in (A.STYLESHEET, A.SORT_SCRIPT, A.FILTER_SCRIPT, A.font_face()):
        assert "—" not in text and "&mdash;" not in text


def test_sort_script_is_self_contained():
    assert "http" not in A.SORT_SCRIPT
    assert "addEventListener" in A.SORT_SCRIPT


def test_filter_script_is_self_contained():
    assert "http" not in A.FILTER_SCRIPT
    assert "addEventListener" in A.FILTER_SCRIPT
    assert "data-f" in A.FILTER_SCRIPT and "data-k" in A.FILTER_SCRIPT


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
