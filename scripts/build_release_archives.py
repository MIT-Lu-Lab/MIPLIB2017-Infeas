"""Build the two per-subset archives the release publishes.

    python scripts/build_release_archives.py --dataset-dir dataset --out-dir dist

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

The CSV comes from a site build, which writes it beside the pages:

    python -m website.build_site --out-dir _site
    python scripts/build_release_archives.py --csv-dir _site
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from website.load import load_index
from website.records import SUBSET_META


def members(samples, subset: str, dataset_dir: Path):
    """(path on disk, name in the archive) for one subset, in published order."""
    info = SUBSET_META[subset]
    for s in sorted((x for x in samples if x.subset == subset),
                    key=lambda x: x.instance):
        for suffix in (".meta.json", ".mps.gz"):
            name = s.stem + suffix
            yield dataset_dir / info["dir"] / name, f"instances/{info['dir']}/{name}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=root / "dataset")
    parser.add_argument("--csv-dir", type=Path, default=root / "_site",
                        help="a site build, which is where the CSV indexes are written")
    parser.add_argument("--index", type=Path,
                        default=root / "metadata" / "site-index.json")
    parser.add_argument("--out-dir", type=Path, default=root / "dist")
    parser.add_argument("--licence", type=Path, default=root / "LICENSE")
    args = parser.parse_args()

    samples = load_index(args.index)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for subset, info in SUBSET_META.items():
        slug = info["slug"]
        csv = args.csv_dir / f"{slug}.csv"
        if not csv.is_file():
            raise SystemExit(f"{csv}: not found; build the site first")
        out = args.out_dir / f"{slug}.zip"
        written = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
            z.write(args.licence, "LICENSE")
            z.write(csv, csv.name)
            for path, name in members(samples, subset, args.dataset_dir):
                if not path.is_file():
                    raise SystemExit(f"{path}: missing, so the archive would be short")
                z.write(path, name)
                written += 1
        print(f"{out}  {out.stat().st_size:,} B  "
              f"{written} instance files plus LICENSE and {csv.name}")


if __name__ == "__main__":
    main()
