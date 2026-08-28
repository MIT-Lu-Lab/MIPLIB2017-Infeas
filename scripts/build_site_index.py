"""Project the published dataset into the site index the build reads.

    pip install --group contracts
    python -m scripts.build_site_index --dataset-dir dataset --out metadata/site-index.json

The sidecars are mostly `path_entries`: the whole bound box of a node, which for
a deep one runs to thousands of entries. The pages show the first twelve and the
count. This writes only what they show, small enough to commit and review.

The published files themselves stay in the release. This projection reads each
one only to record its size; it never parses the MPS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.dataset import DatasetError, scan_dataset
from website import DATASET_DIR, INDEX_FILE
from website.index import INDEX_VERSION, to_record
from website.sidecar import load_sidecar


def scan(dataset_dir: Path) -> list[dict]:
    """One index record per published instance, sorted the way the index stores them."""
    records = []
    try:
        dataset = scan_dataset(dataset_dir)
    except DatasetError as exc:
        raise SystemExit(str(exc)) from exc
    for entry in dataset:
        sample = load_sidecar(entry.sidecar, file_bytes=entry.mps.stat().st_size)
        if (sample.subset, sample.instance) != (entry.subset, entry.instance):
            raise SystemExit(f"{entry.sidecar}: identity does not match its filename and directory")
        if sample.sha256 is None:
            raise SystemExit(
                f"{entry.sidecar}: no SHA-256; run python -m scripts.add_checksums first"
            )
        records.append(to_record(sample))
    records.sort(key=lambda r: (r["subset"], r["instance"]))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--out", type=Path, default=INDEX_FILE)
    args = parser.parse_args()

    records = scan(args.dataset_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Indent one keeps a changed scalar to a short diff without putting each
    # complete record on an unreadably long line.
    args.out.write_text(
        json.dumps({"version": INDEX_VERSION, "records": records}, indent=1, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    counts = {}
    for r in records:
        counts[r["subset"]] = counts.get(r["subset"], 0) + 1
    print(
        f"wrote {len(records)} records ({counts}) to {args.out}, "
        f"{args.out.stat().st_size / 1024:.0f} KB"
    )


if __name__ == "__main__":
    main()
