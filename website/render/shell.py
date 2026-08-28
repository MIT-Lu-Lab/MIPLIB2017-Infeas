"""Jinja environment and the shared context for every page."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ..assets import CSS_NAME, JS_NAME, OG_IMAGE, OG_IMAGE_SIZE
from ..content import NAME, TAGLINE
from ..domain import SUBSET_SPECS
from ..urls import page_url, rel, site_file

_NAV = (
    ("overview", "", "Overview", ""),
    ("primal", SUBSET_SPECS["primal"].slug + "/", SUBSET_SPECS["primal"].label, "Primal"),
    ("dual", SUBSET_SPECS["dual"].slug + "/", SUBSET_SPECS["dual"].label, "Dual"),
    ("guide", "guide/", "Guide", ""),
    ("download", "download/", "Download", ""),
    ("about", "about/", "About", ""),
)

_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape(("html",)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def page(
    template_name: str,
    title: str,
    active: str,
    page_rel: str,
    narrow: bool = False,
    *,
    description: str = "",
    site_url: str | None = None,
    **context: object,
) -> str:
    """Render one page template with the shared document context."""

    canonical = page_url(site_url, page_rel) if site_url else None
    image = site_file(site_url, OG_IMAGE) if site_url else None
    context.update(
        title=title,
        document_title=title if title == NAME else f"{title} \N{MIDDLE DOT} {NAME}",
        page_description=description,
        canonical=canonical,
        image=image,
        image_size=OG_IMAGE_SIZE,
        image_alt=f"{NAME}: {TAGLINE}",
        twitter_card="summary_large_image" if image else "summary",
        site_name=NAME,
        css_href=rel(page_rel, f"assets/{CSS_NAME}"),
        js_src=rel(page_rel, f"assets/{JS_NAME}"),
        root_href=rel(page_rel, ""),
        view=active if active in SUBSET_SPECS else "",
        narrow=narrow,
        nav=tuple(
            {
                "href": rel(page_rel, href),
                "label": label,
                "short": short,
                "current": key == active,
            }
            for key, href, label, short in _NAV
        ),
    )
    return _ENV.get_template(template_name).render(context)
