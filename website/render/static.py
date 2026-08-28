"""Guide, download, and about pages."""

from __future__ import annotations

from .. import content
from ..domain import SUBSET_SPECS, CollectionTotals, Subset
from ..urls import rel
from .shell import page

GUIDE_PAGE = "guide/index.html"
DOWNLOAD_PAGE = "download/index.html"
ABOUT_PAGE = "about/index.html"


def render_guide(imported_sources: int, site_url: str | None = None) -> str:
    """Render the sidecar field reference."""

    return page(
        "guide.html",
        "Reading a file",
        active="guide",
        page_rel=GUIDE_PAGE,
        narrow=True,
        description=content.GUIDE_DESCRIPTION,
        site_url=site_url,
        schema_href=rel(GUIDE_PAGE, content.SIDECAR_SCHEMA_PATH),
        imported_sources_note=content.imported_sources_note(imported_sources),
    )


def render_download(
    totals: CollectionTotals,
    sizes: dict[Subset, int],
    release_base_url: str | None = None,
    site_url: str | None = None,
) -> str:
    """Render the archive and index download links."""

    count = totals["n_samples"]
    return page(
        "download.html",
        "Download",
        active="download",
        page_rel=DOWNLOAD_PAGE,
        narrow=True,
        description=content.DOWNLOAD_DESCRIPTION,
        site_url=site_url,
        instance_count=f"{content.fmt_int(count)} {'instance' if count == 1 else 'instances'}",
        total_size=content.fmt_bytes(sum(sizes.values())),
        cards=tuple(
            {
                "info": info,
                "size": content.fmt_bytes(sizes[subset]),
                "zip_href": (f"{release_base_url}/{info.slug}.zip" if release_base_url else None),
                "csv_href": rel(DOWNLOAD_PAGE, f"{info.slug}.csv"),
            }
            for subset, info in SUBSET_SPECS.items()
        ),
    )


def render_about(site_url: str | None = None) -> str:
    """Render production, provenance, and licence background."""

    return page(
        "about.html",
        "About",
        active="about",
        page_rel=ABOUT_PAGE,
        narrow=True,
        description=content.ABOUT_DESCRIPTION,
        site_url=site_url,
        licence_href=rel(ABOUT_PAGE, "LICENSE.txt"),
    )
