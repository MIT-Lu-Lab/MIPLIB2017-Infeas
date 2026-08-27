"""Record each published MPS file's SHA-256 in its sidecar.

    python scripts/add_checksums.py [--dataset-dir dataset]

Byte sizes catch a truncated download; they do not catch a corrupted one. The
sidecar carries the hash so the CSV indexes can publish it without the build
having to read 2.4 GB on every run.

Run this after any change to the published files.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def sha256(path, chunk=8 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "dataset")
    args = parser.parse_args()

    files = sorted(args.dataset_dir.glob("*/*.mps.gz"))
    print(f"hashing {len(files)} files", flush=True)

    t0 = time.time()
    for n, mps in enumerate(files, 1):
        meta_path = mps.with_name(mps.name.removesuffix(".mps.gz") + ".meta.json")
        if not meta_path.exists():
            raise SystemExit(f"{mps}: no sidecar beside it")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["sha256"] = sha256(mps)
        meta["file_bytes"] = mps.stat().st_size
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        if n % 25 == 0 or n == len(files):
            print(f"  {n}/{len(files)}  ({time.time() - t0:.0f}s)", flush=True)
    print("done")


if __name__ == "__main__":
    main()
