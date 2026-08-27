"""Replace the NAME record of every published MPS with the file's own name.

    python scripts/rewrite_mps_name.py [--dataset-dir dataset] [--check]

CPLEX writes whatever path it read into the NAME record, so every published file
carried the absolute path of the build machine, username included, and named the
*source* instance rather than itself. This rewrites that one line to the
published stem, e.g. `30n20b8_if`, and leaves every other byte of the model
alone.

`--check` reports what would change without writing.
"""

import argparse
import gzip
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def current_name(path):
    """The NAME record's value, or None if the file has no NAME line."""
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if line.startswith("NAME"):
                return line[4:].strip()
            if not line.startswith("*") and line.strip():
                return None      # NAME must come first; anything else means none
    return None


def rewrite(path, stem):
    """Rewrite NAME in place, touching no other line. Returns bytes before/after."""
    before = path.stat().st_size
    tmp = path.with_suffix(path.suffix + ".tmp")
    done = False
    with gzip.open(path, "rt", errors="replace", newline="") as src, \
            gzip.open(tmp, "wt", errors="replace", newline="") as dst:
        for line in src:
            if not done and line.startswith("NAME"):
                dst.write(f"NAME          {stem}\n")
                done = True
            else:
                dst.write(line)
    if not done:                                  # no NAME line: leave the file alone
        tmp.unlink(missing_ok=True)
        return before, before
    shutil.move(str(tmp), str(path))
    return before, path.stat().st_size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "dataset")
    parser.add_argument("--check", action="store_true",
                        help="report what would change, write nothing")
    args = parser.parse_args()

    files = sorted(args.dataset_dir.glob("*/*.mps.gz"))
    print(f"{len(files)} published files", flush=True)

    leaked = [p for p in files if (current_name(p) or "").count("/") > 0]
    print(f"  NAME records carrying a path: {len(leaked)}", flush=True)
    if args.check:
        for p in files[:3]:
            print(f"    {p.name}: {current_name(p)!r} -> "
                  f"{p.name.removesuffix('.mps.gz')!r}")
        return

    t0, delta = time.time(), 0
    for n, p in enumerate(files, 1):
        stem = p.name.removesuffix(".mps.gz")
        b, a = rewrite(p, stem)
        delta += a - b
        if n % 25 == 0 or n == len(files):
            print(f"  {n}/{len(files)}  ({time.time() - t0:.0f}s)", flush=True)
    print(f"done; total size change {delta:+,} bytes")


if __name__ == "__main__":
    main()
