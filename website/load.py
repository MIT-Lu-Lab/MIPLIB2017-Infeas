"""Read the site index and return Sample records. The build's only data input."""

from __future__ import annotations

import json
from pathlib import Path

from .records import INDEX_VERSION, Sample, from_record, with_source_metadata

__all__ = ["collection_totals", "load_index", "subset_bytes"]


def _optional_json(path: Path | str | None) -> dict:
    """Read a JSON mapping, or return {} when the file is absent.

    The MIPLIB metadata is optional by design: without it the pages carry no
    submitter, tags or source description, and it is never fetched at build time.
    """
    if path is None or not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_index(index_path: Path | str,
               miplib_path: Path | str | None = None) -> list[Sample]:
    """Load every published sample from the site index.

    The index carries what the pages render, which is a fifth of a percent of the
    sidecars it was projected from, so a build needs neither the 2.3 GB of
    published files nor the network. scripts/build_site_index.py regenerates it
    from a dataset; that script is the only thing that reads one.

    Args:
        index_path (Path): the site index, normally metadata/site-index.json.
        miplib_path (Path | None): cached MIPLIB 2017 metadata, keyed by instance.

    Returns:
        list[Sample]: sorted by (subset, instance).
    """
    if not Path(index_path).exists():
        raise SystemExit(
            f"{index_path}: no site index. scripts/build_site_index.py writes one "
            "from a checkout of the published dataset.")
    with open(index_path, encoding="utf-8") as f:
        doc = json.load(f)
    if doc.get("version") != INDEX_VERSION:
        raise SystemExit(
            f"{index_path}: index version {doc.get('version')!r}, expected "
            f"{INDEX_VERSION}. Regenerate it with scripts/build_site_index.py.")
    miplib = _optional_json(miplib_path)
    samples = [with_source_metadata(from_record(r), miplib.get(r["instance"]))
               for r in doc["records"]]
    if not samples:
        raise SystemExit(f"{index_path}: holds no records")
    samples.sort(key=lambda s: (s.subset, s.instance))
    return samples


def collection_totals(samples: list[Sample]) -> dict:
    """Headline figures the overview and download pages quote."""
    counts = {}
    for s in samples:
        counts[s.subset] = counts.get(s.subset, 0) + 1
    return {
        "n_samples": len(samples),
        "counts": counts,
        "natural_unbounded": sum(
            s.subset == "dual" and s.dual.natural_unbounded for s in samples),
        "max_vars": max(s.n_vars for s in samples),
        "max_cons": max(s.n_cons for s in samples),
    }


def subset_bytes(samples: list[Sample]) -> dict[str, int]:
    """Per subset, the bytes an archive of it holds: both files of every instance."""
    out = {}
    for s in samples:
        out[s.subset] = out.get(s.subset, 0) + s.total_bytes
    return out
