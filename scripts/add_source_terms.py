"""Record in every published sidecar the terms its source instance carries.

    python scripts/add_source_terms.py --dataset-dir dataset

A sidecar travels with its `.mps.gz`, and someone who takes one file out of an
archive has only that pair to go on. Until now neither said anything about
terms, so the whole question lived in LICENSE, which such a reader never sees.
That was tolerable while the collection claimed one licence for everything. It
is not tolerable now that it does not: 130 of the 262 source instances carry no
licence of record, and a file that says nothing invites the reader to assume the
CC BY-SA the rest of the collection is under.

The terms come from `website.records.source_terms`, the same function the pages
render, so the sidecar and the instance page cannot drift apart. Which case an
instance falls into is decided by MIPLIB's own provenance note, cached in
metadata/miplib_meta.json by scripts/fetch_miplib_meta.py.

Writing this changes every sidecar's size, and metadata/site-index.json records
those sizes, so run scripts/build_site_index.py afterwards and re-upload both.
The .mps.gz files are untouched, and so are the checksums published for them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from website.records import SUBSET_META, source_terms


def sidecars(dataset_dir: Path):
    """Every published sidecar, with the subset it belongs to."""
    for info in SUBSET_META.values():
        subdir = dataset_dir / info["dir"]
        if not subdir.is_dir():
            raise SystemExit(f"{subdir}: not a directory")
        yield from sorted(subdir.glob("*.meta.json"))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=root / "dataset")
    parser.add_argument("--miplib-meta", type=Path,
                        default=root / "metadata" / "miplib_meta.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change and write nothing")
    args = parser.parse_args()

    meta = json.loads(args.miplib_meta.read_text(encoding="utf-8"))

    written = unchanged = 0
    counts: dict[str, int] = {}
    unknown = []
    for path in sidecars(args.dataset_dir):
        sidecar = json.loads(path.read_text(encoding="utf-8"))
        instance = sidecar["instance"]
        entry = meta.get(instance)
        if entry is None:
            # without MIPLIB's note there is no evidence either way, and guessing
            # is what this whole exercise exists to stop
            unknown.append(instance)
            continue
        terms = source_terms(instance, entry.get("imported_from"))
        counts[terms["summary"]] = counts.get(terms["summary"], 0) + 1
        if sidecar.get("source_terms") == terms:
            unchanged += 1
            continue
        sidecar["source_terms"] = terms
        if not args.dry_run:
            path.write_text(json.dumps(sidecar, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
        written += 1

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {written} sidecars, {unchanged} already current")
    for summary, n in sorted(counts.items()):
        print(f"  {n:>4}  {summary}")
    if unknown:
        raise SystemExit(
            f"\n{len(unknown)} instance(s) absent from {args.miplib_meta.name}, so "
            f"their terms are unknown: {', '.join(unknown[:5])}\n"
            "Run scripts/fetch_miplib_meta.py first; a sidecar must not be given "
            "terms that were guessed rather than read off MIPLIB.")
    if not args.dry_run and written:
        print("\nsidecar sizes changed: run scripts/build_site_index.py next, then "
              "re-upload the sidecars and metadata/site-index.json")


if __name__ == "__main__":
    main()
