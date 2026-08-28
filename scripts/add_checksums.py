"""Record each published MPS file's SHA-256 in its sidecar.

    python -m scripts.add_checksums [--dataset-dir dataset]

Byte sizes catch a truncated download; they do not catch a corrupted one. The
sidecar carries the hash so the CSV indexes can publish it without the build
having to read 2.4 GB on every run.

Run this after any change to the published files.
"""

import argparse
import hashlib
import time
from pathlib import Path

from scripts.dataset import DatasetError, read_entry_sidecar, replace_sidecar, scan_dataset
from website import DATASET_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    args = parser.parse_args()

    try:
        dataset = scan_dataset(args.dataset_dir)
    except DatasetError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"hashing {len(dataset)} files", flush=True)

    t0 = time.time()
    for n, entry in enumerate(dataset, 1):
        try:
            meta = read_entry_sidecar(entry)
        except DatasetError as exc:
            raise SystemExit(str(exc)) from exc
        with entry.mps.open("rb") as stream:
            meta["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        meta["file_bytes"] = entry.mps.stat().st_size
        replace_sidecar(entry.sidecar, meta)
        if n % 25 == 0 or n == len(dataset):
            print(f"  {n}/{len(dataset)}  ({time.time() - t0:.0f}s)", flush=True)
    print("done; next: python -m scripts.build_site_index")


if __name__ == "__main__":
    main()
