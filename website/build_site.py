"""CLI: render the whole site from the site index into a static tree.

Run as `python -m website.build_site`.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import replace
from pathlib import Path

from . import load, render
from .assets import CSS_NAME, JS_NAME, SITE_CSS, SITE_JS
from .records import OTHER_SUBSET, SUBSET_META, Sample

DEFAULT_OUT = Path(__file__).resolve().parent / "_out"
_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = _ROOT / "metadata" / "site-index.json"
DEFAULT_MIPLIB = _ROOT / "metadata" / "miplib_meta.json"
FONT_DIR = _ROOT / "fonts"

# Published index columns, per subset, as (header, accessor). The headers ship as
# release assets, so renaming one breaks whatever is reading the CSVs.
_CSV_HEAD = (
    ("instance", lambda s: s.instance),
    ("n_vars", lambda s: s.n_vars),
    ("n_cons", lambda s: s.n_cons),
    ("nnz", lambda s: s.nnz),
)
_CSV_TAIL = (
    ("file_bytes", lambda s: s.file_bytes),
    ("sha256", lambda s: s.sha256),
    ("mps_filename", lambda s: s.stem + ".mps.gz"),
)
_CSV_COLUMNS = {
    "primal": (*_CSV_HEAD,
               ("depth", lambda s: s.primal.depth),
               ("bound_changes", lambda s: s.primal.bound_changes),
               *_CSV_TAIL),
    "dual": (*_CSV_HEAD,
             ("bounds_dropped", lambda s: s.dual.bounds_dropped),
             ("rows_dropped", lambda s: s.dual.rows_dropped),
             *_CSV_TAIL),
}


def _write_manifest(out_dir: Path, subset: str, info: dict,
                    samples: list[Sample]) -> str:
    """Write <slug>.csv, one row per published instance. Returns its relative path
    so the pruner counts it as generated rather than stale."""
    cols = _CSV_COLUMNS[subset]
    rows = [s for s in samples if s.subset == subset]
    path = out_dir / f"{info['slug']}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([header for header, _ in cols])
        for s in rows:
            writer.writerow([get(s) for _, get in cols])
    return path.relative_to(out_dir).as_posix()


def release_urls(samples: list[Sample], base_url: str | None) -> dict[str, str]:
    """Map every published filename to its GitHub Release asset URL.

    Release assets live at `<base>/<filename>`, so one base URL replaces a
    per-file map. Returns {} when no base URL is configured, which leaves the
    download buttons as disabled placeholders.
    """
    if not base_url:
        return {}
    if not base_url.startswith(("http://", "https://")):
        raise SystemExit(
            f"--release-base-url must be an absolute URL, got {base_url!r}. "
            "Without a scheme every download link on the site would be relative "
            "and dead.")
    base = base_url.rstrip("/")
    urls = {}
    for s in samples:
        urls[s.stem + ".mps.gz"] = f"{base}/{s.stem}.mps.gz"
        urls[s.stem + ".meta.json"] = f"{base}/{s.stem}.meta.json"
    return urls


def _write_assets(out_dir: Path) -> set[str]:
    """Write the stylesheet and the scripts the pages link to.

    Their names carry a digest of their contents, so a reader cannot be served
    this build's HTML against the last build's stylesheet, and _prune can tell
    the two apart.
    """
    d = out_dir / "assets"
    d.mkdir(parents=True, exist_ok=True)
    (d / CSS_NAME).write_text(SITE_CSS, encoding="utf-8")
    (d / JS_NAME).write_text(SITE_JS, encoding="utf-8")
    return {f"assets/{CSS_NAME}", f"assets/{JS_NAME}"}


def _write_nojekyll(out_dir: Path) -> str:
    """Tell Pages to serve the tree as-is.

    Without it Jekyll drops any path beginning with an underscore, and it belongs
    to the build rather than to whoever set the output directory up: the site is
    deployed from a fresh artifact, so nothing carries a stray file across.
    """
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return ".nojekyll"


def _copy_fonts(out_dir: Path) -> set[str]:
    """Copy the self-hosted faces into the output. Returns their relative paths.

    The pages reference these, so a build that did not carry them would produce a
    site that renders only in whatever the reader has installed.
    """
    dest = out_dir / "fonts"
    dest.mkdir(parents=True, exist_ok=True)
    rels = set()
    for src in sorted(FONT_DIR.iterdir()):
        if src.is_file():
            shutil.copyfile(src, dest / src.name)
            rels.add(f"fonts/{src.name}")
    return rels


def _write(out_dir: Path, rel: str, html: str) -> None:
    path = out_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _prune(out_dir: Path, keep_rels: set[str]) -> None:
    """Delete generated files this build did not write, and any directory they
    leave empty.

    Only files the build itself produces are candidates: pages, the CSV indexes,
    the fonts and the hashed stylesheet and scripts. Anything else in the output
    directory belongs to whoever put it there, a CNAME for a custom domain being
    the usual case.
    """
    # materialise the walk before deleting: rglob is a generator over the tree it
    # is walking, and removing entries mid-iteration is undefined
    generated = (list(out_dir.rglob("index.html")) + list(out_dir.glob("*.csv"))
                 + list((out_dir / "fonts").glob("*"))
                 + list((out_dir / "assets").glob("*")))
    for path in generated:
        rel = path.relative_to(out_dir).as_posix()
        if rel in keep_rels:
            continue
        path.unlink()
        d = path.parent
        while d != out_dir and not any(d.iterdir()):
            parent = d.parent
            d.rmdir()
            d = parent


def build(index_path: Path | str, out_dir: Path | str,
          release_base_url: str | None = None, site_url: str | None = None,
          miplib_path: Path | None = None) -> int:
    """Render every page. Returns the number of pages written.

    Args:
        index_path (Path): the site index, the build's only data input.
        out_dir (Path): where the static tree lands.
        release_base_url (str | None): the GitHub Release download prefix. When
            given, every instance's download URLs are derived from it.
        site_url (str | None): public URL of the published site, shown in the
            citation block.
        miplib_path (Path | None): cached MIPLIB 2017 metadata.
    """
    out_dir = Path(out_dir)
    samples = load.load_index(index_path, miplib_path)
    if release_base_url:
        urls = release_urls(samples, release_base_url)
        samples = [replace(x,
                           mps_url=urls.get(x.stem + ".mps.gz"),
                           meta_url=urls.get(x.stem + ".meta.json"))
                   for x in samples]

    totals = load.collection_totals(samples)
    sizes = load.subset_bytes(samples)
    by_key = {(s.subset, s.instance): s for s in samples}

    written = 0
    rels = set()

    def _emit(rel: str, html: str) -> None:
        nonlocal written
        _write(out_dir, rel, html)
        rels.add(rel)
        written += 1

    _emit("index.html", render.render_overview(totals, site_url, release_base_url))
    _emit("download/index.html",
          render.render_download(totals, release_base_url, sizes))
    _emit("about/index.html", render.render_about())
    _emit("guide/index.html", render.render_guide())

    for subset, info in SUBSET_META.items():
        _emit(f"{info['slug']}/index.html",
              render.render_browse(subset, samples, release_base_url))
        for s in (x for x in samples if x.subset == subset):
            cross = by_key.get((OTHER_SUBSET[subset], s.instance))
            _emit(s.page_path + "index.html", render.render_sample(s, cross))
        rels.add(_write_manifest(out_dir, subset, info, samples))

    rels |= _copy_fonts(out_dir)
    rels |= _write_assets(out_dir)
    rels.add(_write_nojekyll(out_dir))
    _prune(out_dir, rels)
    return written


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX,
                        help="site index; scripts/build_site_index.py writes it")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--release-base-url", default=None,
                        help="GitHub Release download prefix, e.g. "
                             "https://github.com/OWNER/REPO/releases/download/v1.0 . "
                             "Given this, download links are generated; without it "
                             "they stay disabled placeholders.")
    parser.add_argument("--miplib", type=Path, default=DEFAULT_MIPLIB,
                        help="cached MIPLIB 2017 metadata; absent is fine")
    parser.add_argument("--site-url", default=None,
                        help="public URL of the published site, used in the citation "
                             "block, e.g. https://ORG.github.io/REPO")
    args = parser.parse_args()
    n = build(args.index, args.out_dir, release_base_url=args.release_base_url,
              site_url=args.site_url, miplib_path=args.miplib)
    print(f"wrote {n} pages to {args.out_dir}")


if __name__ == "__main__":
    main()
