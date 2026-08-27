"""Project the published dataset into the site index the build reads.

    python scripts/build_site_index.py --dataset-dir dataset --out metadata/site-index.json

The 334 sidecars come to 146 MB, mostly `path_entries`: the whole bound box of a
node, which for a deep one runs to thousands of entries. The pages show the first
twelve and the count. This writes out what they show, which is a fifth of a
percent of that, small enough to commit and to review in a diff.

The published files themselves stay in the release. This is the only thing in the
repository that reads them, and it reads each one only to size it, unless a
sidecar is missing its checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from website.records import INDEX_VERSION, SUBSET_META, sample_from_meta, to_record


def sha256(path: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def scan(dataset_dir: Path) -> list[dict]:
    """One index record per published instance, sorted the way the index stores them."""
    records = []
    for info in SUBSET_META.values():
        subdir = dataset_dir / info["dir"]
        if not subdir.is_dir():
            raise SystemExit(f"{subdir}: not a directory")
        for meta_path in sorted(subdir.glob("*.meta.json")):
            mps_path = meta_path.with_name(
                meta_path.name.removesuffix(".meta.json") + ".mps.gz")
            if not mps_path.exists():
                raise SystemExit(f"{meta_path}: no .mps.gz beside it")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            # scripts/add_checksums.py records this; fall back to computing it so a
            # sidecar written before that script still yields a complete index
            if not meta.get("sha256"):
                meta["sha256"] = sha256(mps_path)
            records.append(to_record(sample_from_meta(
                meta, mps_path.stat().st_size, meta_path.stat().st_size)))
    records.sort(key=lambda r: (r["subset"], r["instance"]))
    return records


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=root / "dataset")
    parser.add_argument("--out", type=Path, default=root / "metadata" / "site-index.json")
    args = parser.parse_args()

    records = scan(args.dataset_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # one record per line is unreadable at 334 records and one key per line is
    # 30k lines; indent=1 keeps a changed field to a one-line diff
    args.out.write_text(
        json.dumps({"version": INDEX_VERSION, "records": records},
                   indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    counts = {}
    for r in records:
        counts[r["subset"]] = counts.get(r["subset"], 0) + 1
    print(f"wrote {len(records)} records ({counts}) to {args.out}, "
          f"{args.out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
