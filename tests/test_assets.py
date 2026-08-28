import hashlib
import re

from website import assets as A

TOKENS = (
    "--paper",
    "--raise",
    "--ink",
    "--muted",
    "--rule",
    "--rule-soft",
    "--primal",
    "--primal-wash",
    "--dual",
    "--dual-wash",
)


def test_final_stylesheet_carries_the_complete_adaptive_palette():
    root = re.search(r":root\{(.*?)\}", A.SITE_CSS, re.S)
    assert root
    for token in TOKENS:
        assert re.search(rf"{re.escape(token)}:light-dark\([^)]*,[^)]*\)", root.group(1))


def test_og_renderer_can_select_its_deterministic_dark_theme():
    assert ':root[data-theme="dark"]{color-scheme:dark}' in A.SITE_CSS


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
