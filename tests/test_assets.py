import hashlib
import re

from website import assets as A

COLOUR_TOKENS = (
    "--paper",
    "--raise",
    "--ink",
    "--muted",
    "--muted-strong",
    "--rule",
    "--rule-soft",
    "--primal",
    "--primal-wash",
    "--dual",
    "--dual-wash",
    "--shared",
    "--shared-wash",
    "--on-view",
)

_SCREEN = r"\n:root\{(.*?)\n\}"
_PAPER = r"@media print\{\s*:root\{(.*?)\n  \}"


def _block(pattern: str) -> str:
    found = re.search(pattern, A.SITE_CSS, re.S)
    assert found, pattern
    return found.group(1)


def test_every_colour_token_is_defined_for_screen_and_for_paper():
    """The print block is a second palette, not an override of a few colours.

    A token added to one and not the other prints as whatever it inherits, and
    nothing but a printed page would ever show it.
    """
    screen, paper = _block(_SCREEN), _block(_PAPER)
    for token in COLOUR_TOKENS:
        assert re.search(rf"{re.escape(token)}:#[0-9A-Fa-f]{{6}}", screen), token
        assert re.search(rf"{re.escape(token)}:#[0-9A-Fa-f]{{6}}", paper), token


def test_the_site_is_one_dark_theme_and_paper_is_the_exception():
    """The scheme is declared once and only print swaps it, so no rule anywhere
    else has to ask which theme it is in."""
    assert "color-scheme:dark" in _block(_SCREEN)
    assert "color-scheme:light" in _block(_PAPER)
    assert "light-dark(" not in A.SITE_CSS


def test_asset_names_are_derived_from_the_published_bytes():
    css_hash = hashlib.sha256(A.SITE_CSS.encode()).hexdigest()[:12]
    js_hash = hashlib.sha256(A.SITE_JS.encode()).hexdigest()[:12]
    expected_css = f"site.{css_hash}.css"
    expected_js = f"site.{js_hash}.js"
    assert expected_css == A.CSS_NAME
    assert expected_js == A.JS_NAME


def test_stylesheet_fetches_no_third_party_urls():
    assert "http" not in A.SITE_CSS


def test_assets_do_not_use_em_dashes():
    for text in (A.SITE_CSS, A.SITE_JS):
        assert "\N{EM DASH}" not in text and "&mdash;" not in text
