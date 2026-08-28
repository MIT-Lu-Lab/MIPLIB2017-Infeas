"""Record in every published sidecar the terms its source instance carries.

    python -m scripts.add_source_terms --dataset-dir dataset

A sidecar travels with its `.mps.gz`, and someone who takes one file out of an
archive has only that pair to go on. Until now neither said anything about
terms, so the whole question lived in LICENSE, which such a reader never sees.
That was tolerable while the collection claimed one licence for everything. It
is not tolerable now that the sources do not share one: a file that says nothing
invites the reader to assume the terms of a different source.

The terms come from `website.domain.source_terms`, the same function the pages
render, so the sidecar and the instance page cannot drift apart. Which case an
instance falls into is decided by MIPLIB's own provenance note, cached in
metadata/miplib_meta.json by scripts/fetch_miplib_meta.py.

Writing this changes every sidecar's size, and metadata/site-index.json records
those sizes, so run ``python -m scripts.build_site_index`` afterwards and re-upload both.
The .mps.gz files are untouched, and so are the checksums published for them.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

from scripts.dataset import (
    DatasetEntry,
    DatasetError,
    read_entry_sidecar,
    replace_sidecar,
    scan_dataset,
    sidecar_text,
)
from website import DATASET_DIR, MIPLIB_FILE
from website.domain import source_terms
from website.jsonio import JsonError, read_json


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--miplib-meta", type=Path, default=MIPLIB_FILE)
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would change and write nothing"
    )
    args = parser.parse_args()

    try:
        raw_meta = read_json(args.miplib_meta)
        if not isinstance(raw_meta, dict):
            raise DatasetError(f"{args.miplib_meta}: metadata cache must be a JSON object")
        source_meta = cast(dict[str, dict[str, Any]], raw_meta)
        dataset = scan_dataset(args.dataset_dir)
    except (DatasetError, JsonError) as exc:
        raise SystemExit(str(exc)) from exc

    unchanged = 0
    counts: dict[str, int] = {}
    unknown: list[str] = []
    planned: list[DatasetEntry] = []
    for entry in dataset:
        path = entry.sidecar
        raw = path.read_text(encoding="utf-8")
        try:
            sidecar = read_entry_sidecar(entry)
        except DatasetError as exc:
            raise SystemExit(str(exc)) from exc
        instance = sidecar["instance"]
        source = source_meta.get(instance)
        if source is None:
            # without MIPLIB's note there is no evidence either way, and guessing
            # is what this whole exercise exists to stop
            unknown.append(instance)
            continue
        terms = source_terms(instance, source.get("imported_from"))
        counts[terms["summary"]] = counts.get(terms["summary"], 0) + 1
        if sidecar.get("source_terms") == terms:
            unchanged += 1
            continue
        # Re-serialising the file unchanged has to reproduce it byte for byte. If
        # it does not, this script's formatting differs from the miners' and a
        # write would reflow every sidecar instead of adding one field.
        if sidecar_text(sidecar) != raw:
            raise SystemExit(
                f"{path}: re-serialising it changes bytes beyond the new field, so "
                "writing would reflow every sidecar. Match the miners' formatting "
                "before publishing anything."
            )
        planned.append(entry)

    if unknown:
        raise SystemExit(
            f"\n{len(unknown)} instance(s) absent from {args.miplib_meta.name}, so "
            f"their terms are unknown: {', '.join(unknown[:5])}\n"
            "Run python -m scripts.fetch_miplib_meta first; a sidecar must not be given "
            "terms that were guessed rather than read off MIPLIB."
        )
    if not args.dry_run:
        for entry in planned:
            try:
                sidecar = read_entry_sidecar(entry)
            except DatasetError as exc:
                raise SystemExit(str(exc)) from exc
            instance = sidecar["instance"]
            source = source_meta[instance]
            sidecar["source_terms"] = source_terms(instance, source.get("imported_from"))
            replace_sidecar(entry.sidecar, sidecar)

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {len(planned)} sidecars, {unchanged} already current")
    for summary, n in sorted(counts.items()):
        print(f"  {n:>4}  {summary}")
    if not args.dry_run and planned:
        print(
            "\nsidecar sizes changed: run python -m scripts.build_site_index next, then "
            "re-upload the sidecars and metadata/site-index.json"
        )


if __name__ == "__main__":
    main()
