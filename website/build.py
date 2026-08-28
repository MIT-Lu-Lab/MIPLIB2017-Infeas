"""Build and atomically publish the static site."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from . import INDEX_FILE, MIPLIB_FILE, ROOT, assets, catalog, render
from .domain import (
    OTHER_SUBSET,
    SUBSET_SPECS,
    collection_totals,
    subset_bytes,
)
from .index import load_collection
from .output import OutputError, publish_atomically
from .urls import normalize_release_base_url, normalize_site_url, page_url

DEFAULT_OUT = ROOT / "_site"
_FONT_DIR = ROOT / "fonts"
_SCHEMA_DIR = ROOT / "schema"
_LICENSE_FILE = ROOT / "LICENSE"
_OG_IMAGE_FILE = ROOT / "og.png"


def _static_files() -> list[tuple[str, bytes]]:
    if not _FONT_DIR.is_dir() or not _SCHEMA_DIR.is_dir():
        raise ValueError("the fonts and schema directories must be present")

    files: list[tuple[str, bytes]] = []
    for path in sorted(_FONT_DIR.iterdir(), key=lambda item: item.name):
        if path.is_file():
            files.append((f"fonts/{path.name}", path.read_bytes()))
    for path in sorted(_SCHEMA_DIR.rglob("*")):
        if path.is_file():
            relative = path.relative_to(_SCHEMA_DIR).as_posix()
            files.append((f"schema/{relative}", path.read_bytes()))
    files.extend(
        (
            ("LICENSE.txt", _LICENSE_FILE.read_bytes()),
            (assets.OG_IMAGE, _OG_IMAGE_FILE.read_bytes()),
        )
    )
    return files


def _sitemap(site_url: str, page_paths: Sequence[str]) -> str:
    urls = sorted(page_url(site_url, path) for path in page_paths)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        *(f"  <url><loc>{xml_escape(url)}</loc></url>" for url in urls),
        "</urlset>",
    ]
    return "\n".join(lines) + "\n"


def build(
    index_path: Path | str,
    out_dir: Path | str,
    release_base_url: str | None = None,
    site_url: str | None = None,
    miplib_path: Path | str | None = None,
) -> int:
    """Build the complete site and replace an owned output tree atomically."""
    site_url = normalize_site_url(site_url)
    release_base_url = normalize_release_base_url(release_base_url)
    samples = load_collection(index_path, miplib_path)
    totals = collection_totals(samples)
    sizes = subset_bytes(samples)
    by_key = {(sample.subset, sample.instance): sample for sample in samples}
    files: list[tuple[str, bytes]] = []
    pages: list[str] = []

    def emit_page(path: str, html: str) -> None:
        files.append((path, html.encode("utf-8")))
        pages.append(path)

    emit_page("index.html", render.render_overview(totals, site_url, release_base_url))
    emit_page(
        "download/index.html",
        render.render_download(totals, sizes, release_base_url, site_url),
    )
    emit_page("about/index.html", render.render_about(site_url))
    imported_sources = len({sample.instance for sample in samples if sample.imported_from})
    emit_page("guide/index.html", render.render_guide(imported_sources, site_url))

    for subset, info in SUBSET_SPECS.items():
        subset_samples = [sample for sample in samples if sample.subset == subset]
        rows = catalog.subset_rows(subset, samples)
        emit_page(
            render.browse_page_rel(subset),
            render.render_browse(subset, samples, release_base_url, site_url),
        )
        for sample in subset_samples:
            cross = by_key.get((OTHER_SUBSET[subset], sample.instance))
            emit_page(
                sample.page_path + "index.html",
                render.render_sample(sample, cross, site_url, release_base_url),
            )
        files.extend(
            (
                (f"{info.slug}.csv", catalog.csv_index(subset, rows)),
                (
                    f"{info.slug}.json",
                    catalog.subset_index(subset, info, rows, release_base_url),
                ),
            )
        )

    files.extend(
        (
            ("index.json", catalog.collection_index(totals, site_url, release_base_url)),
            (f"assets/{assets.CSS_NAME}", assets.SITE_CSS.encode("utf-8")),
            (f"assets/{assets.JS_NAME}", assets.SITE_JS.encode("utf-8")),
            (".nojekyll", b""),
        )
    )
    files.extend(_static_files())
    if site_url:
        files.append(("sitemap.xml", _sitemap(site_url, pages).encode("utf-8")))
    publish_atomically(files, out_dir)
    return len(pages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        default=INDEX_FILE,
        help="site index; python -m scripts.build_site_index writes it",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--release-base-url",
        help=(
            "GitHub Release download prefix, for example "
            "https://github.com/OWNER/REPO/releases/download/v1.0; "
            "without it download links remain disabled placeholders"
        ),
    )
    parser.add_argument(
        "--miplib",
        type=Path,
        default=MIPLIB_FILE,
        help="cached MIPLIB 2017 attribution and description metadata",
    )
    parser.add_argument(
        "--site-url",
        help="public base URL, for example https://ORG.github.io/REPO",
    )
    args = parser.parse_args()
    try:
        count = build(
            args.index,
            args.out_dir,
            release_base_url=args.release_base_url,
            site_url=args.site_url,
            miplib_path=args.miplib,
        )
    except (OSError, OutputError, ValueError) as exc:
        parser.error(str(exc))
    print(f"wrote {count} pages to {args.out_dir}")


if __name__ == "__main__":
    main()
