"""Build the two per-subset archives the release publishes.

    python -m scripts.build_release_archives --dataset-dir dataset --out-dir dist

Each archive is a whole subset, and it is what most readers actually take away:
the notice and the index have to be inside it, not only on the release page.
The layout is the published one and is a contract, since anyone who unpacked
v1.0 has scripts pointing at these paths:

    LICENSE
    <subset>.csv
    instances/<dir>/<instance><suffix>.meta.json
    instances/<dir>/<instance><suffix>.mps.gz

Stored, not deflated, matching what is published. The instances are gzipped
already and deflating them again buys nothing for the time it costs.

The CSV is generated from the same catalogue code as the site, so building a
release does not depend on a pre-existing site output directory.
"""

from __future__ import annotations

import argparse
import tempfile
import zipfile
from collections.abc import Iterator, Sequence
from pathlib import Path

from scripts.dataset import DatasetEntry, DatasetError, scan_dataset
from website import DATASET_DIR, INDEX_FILE, ROOT
from website.catalog import csv_index, subset_rows
from website.domain import SUBSET_SPECS, Subset
from website.index import SiteIndexError, load_collection

type ArchiveSource = Path | bytes


def members(entries: Sequence[DatasetEntry], subset: Subset) -> Iterator[tuple[Path, str]]:
    """(path on disk, name in the archive) for one subset, in published order."""
    info = SUBSET_SPECS[subset]
    for entry in entries:
        if entry.subset != subset:
            continue
        for path in (entry.sidecar, entry.mps):
            yield path, f"instances/{info.directory}/{path.name}"


def write_archive(out: Path, entries: Sequence[tuple[ArchiveSource, str]]) -> None:
    """Replace one archive only after its complete temporary copy is closed."""
    with tempfile.NamedTemporaryFile(
        dir=out.parent, prefix=f".{out.stem}.", suffix=".zip", delete=False
    ) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_STORED, allowZip64=True) as archive:
            for source, name in entries:
                if isinstance(source, bytes):
                    archive.writestr(name, source)
                else:
                    archive.write(source, name)
        temporary.replace(out)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--index", type=Path, default=INDEX_FILE)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--licence", type=Path, default=ROOT / "LICENSE")
    args = parser.parse_args()

    try:
        samples = load_collection(args.index)
        dataset = scan_dataset(args.dataset_dir)
    except (DatasetError, SiteIndexError) as exc:
        parser.error(str(exc))
    if not args.licence.is_file():
        raise SystemExit(f"{args.licence}: licence not found")
    sample_keys = {(sample.subset, sample.instance) for sample in samples}
    dataset_keys = {(entry.subset, entry.instance) for entry in dataset}
    if sample_keys != dataset_keys:
        missing = sorted(sample_keys - dataset_keys)
        extra = sorted(dataset_keys - sample_keys)
        details: list[str] = []
        if missing:
            details.append(f"missing from dataset: {missing[:5]}")
        if extra:
            details.append(f"absent from index: {extra[:5]}")
        parser.error("dataset inventory differs from the site index; " + "; ".join(details))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for subset, info in SUBSET_SPECS.items():
        out = args.out_dir / f"{info.slug}.zip"
        csv_name = f"{info.slug}.csv"
        csv_bytes = csv_index(subset, subset_rows(subset, samples))
        instance_files = tuple(members(dataset, subset))
        write_archive(
            out,
            ((args.licence, "LICENSE"), (csv_bytes, csv_name), *instance_files),
        )
        written = len(instance_files)
        print(
            f"{out}  {out.stat().st_size:,} B  {written} instance files plus LICENSE and {csv_name}"
        )


if __name__ == "__main__":
    main()
