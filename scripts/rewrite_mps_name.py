"""Replace the NAME record of every published MPS with the file's own name.

    python -m scripts.rewrite_mps_name [--dataset-dir dataset] [--check]

CPLEX writes whatever path it read into the NAME record, so every published file
carried the absolute path of the build machine, username included, and named the
*source* instance rather than itself. This rewrites that one line to the
published stem, e.g. `30n20b8_if`, and leaves every other byte of the model
alone.

`--check` reports what would change without writing.
"""

import argparse
import gzip
import time
from pathlib import Path

from scripts.dataset import DatasetError, scan_dataset
from website import DATASET_DIR


def current_name(path):
    """The NAME record's value, or None if the file has no NAME line."""
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if line.startswith("NAME"):
                return line[4:].strip()
            if not line.startswith("*") and line.strip():
                return None  # NAME must come first; anything else means none
    return None


def rewrite(path, stem):
    """Rewrite NAME in place, touching no other line. Returns bytes before/after."""
    before = path.stat().st_size
    tmp = path.with_suffix(path.suffix + ".tmp")
    done = False
    with (
        gzip.open(path, "rt", errors="replace", newline="") as src,
        gzip.open(tmp, "wt", errors="replace", newline="") as dst,
    ):
        for line in src:
            if not done and line.startswith("NAME"):
                dst.write(f"NAME          {stem}\n")
                done = True
            else:
                dst.write(line)
    if not done:  # no NAME line: leave the file alone
        tmp.unlink(missing_ok=True)
        return before, before
    tmp.replace(path)
    return before, path.stat().st_size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument(
        "--check", action="store_true", help="report what would change, write nothing"
    )
    args = parser.parse_args()

    try:
        dataset = scan_dataset(args.dataset_dir)
    except DatasetError as exc:
        raise SystemExit(str(exc)) from exc
    records = [(entry.mps, current_name(entry.mps), entry.stem) for entry in dataset]
    changes = [record for record in records if record[1] != record[2]]
    print(f"{len(dataset)} published files; {len(changes)} NAME records to rewrite", flush=True)
    if args.check:
        for path, name, stem in changes[:3]:
            print(f"    {path.name}: {name!r} -> {stem!r}")
        return

    t0, delta = time.time(), 0
    for n, (path, _, stem) in enumerate(changes, 1):
        before, after = rewrite(path, stem)
        delta += after - before
        if n % 25 == 0 or n == len(changes):
            print(f"  {n}/{len(changes)}  ({time.time() - t0:.0f}s)", flush=True)
    print(f"done; total size change {delta:+,} bytes")
    if changes:
        print("next: python -m scripts.add_checksums, then python -m scripts.build_site_index")


if __name__ == "__main__":
    main()
