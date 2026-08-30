"""The site root."""

from __future__ import annotations

from .. import content
from ..domain import SUBSET_SPECS, CollectionTotals
from ..urls import rel, site_file
from .shell import page

PAGE = "index.html"


def _dataset_jsonld(
    totals: CollectionTotals, site_url: str | None, release_base_url: str | None
) -> dict[str, object]:
    """Return the schema.org/Dataset description read by dataset search engines."""

    doc: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": content.NAME,
        "alternateName": "Primal- and Dual-Infeasible Linear Programs from MIPLIB 2017",
        "description": content.collection_summary(totals),
        "keywords": [
            "linear programming",
            "infeasibility detection",
            "unbounded linear programs",
            "benchmark",
            "MIPLIB",
            "mathematical optimization",
        ],
        "creator": [
            {"@type": "Person", "name": "Haihao Lu"},
            {"@type": "Person", "name": "Bo Tang"},
        ],
        "isBasedOn": "https://miplib.zib.de/",
        "encodingFormat": ["application/gzip", "application/json"],
    }
    if site_url:
        doc["url"] = site_url
        doc["usageInfo"] = site_file(site_url, "LICENSE.txt")
    if release_base_url:
        doc["distribution"] = [
            {
                "@type": "DataDownload",
                "name": f"{info.label} instances",
                "encodingFormat": "application/zip",
                "contentUrl": f"{release_base_url}/{info.slug}.zip",
            }
            for info in SUBSET_SPECS.values()
        ]
    return doc


def render_overview(
    totals: CollectionTotals, site_url: str | None = None, release_base_url: str | None = None
) -> str:
    """Render the site root."""

    counts = totals["counts"]
    primal = counts["primal"]
    dual = counts["dual"]
    return page(
        "overview.html",
        content.NAME,
        active="overview",
        page_rel=PAGE,
        narrow=True,
        description=content.overview_description(totals),
        site_url=site_url,
        dataset_jsonld=_dataset_jsonld(totals, site_url, release_base_url),
        tagline=content.TAGLINE,
        name=content.NAME,
        n_samples=content.fmt_int(totals["n_samples"]),
        n_primal=content.fmt_int(primal),
        n_dual=content.fmt_int(dual),
        primal_verb="has" if primal == 1 else "have",
        dual_verb="is" if dual == 1 else "are",
        max_vars=content.fmt_int(totals["max_vars"]),
        max_cons=content.fmt_int(totals["max_cons"]),
        figure_screen=rel(PAGE, content.FIGURE_SCREEN),
        figure_print=rel(PAGE, content.FIGURE_PRINT),
        figure_alt=content.FIGURE_ALT,
        figure_caption=content.FIGURE_CAPTION,
        cards=tuple(
            {
                "tone": info.tone,
                "slug": info.slug,
                "label": info.label,
                "count": content.fmt_int(counts[subset]),
                "blurb": content.subset_card(subset, counts[subset], totals["natural_unbounded"]),
            }
            for subset, info in SUBSET_SPECS.items()
        ),
        citation_url=site_url or content.PUBLIC_SITE_URL,
    )
