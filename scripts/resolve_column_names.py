"""Resolve the column indices in each sidecar to the real MPS column names.

    python scripts/resolve_column_names.py [--dataset-dir dataset]

The miners record variables by 0-based column index, which is what they have in
hand. Printing those as `x643` invents a name: column 643 of `30n20b8_if` is
really `S_2`, and worse, 23 of the published instances contain columns actually
named `x<digits>` at different indices, so a reader looking the printed label up
gets a different variable rather than nothing.

This reads the COLUMNS section of each published MPS once and writes the real
names back into the sidecar:

    branch_var_name    the branched column                     (primal)
    path_head_named    the first HEAD_LIMIT accumulated bounds (primal)
    drops[].name       the relaxed column, per bound drop      (dual)

`path_entries` keeps its index form: the largest carries 642,147 entries and
names are longer than indices. The sidecar records that convention in
`path_entries_are_column_indices`.
"""

import argparse
import gzip
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HEAD_LIMIT = 12
ENTRY_RE = re.compile(r"^x(\d+)(<=|>=)(.+)$")

SUBSETS = {
    "primal": {"dir": "infeasible", "suffix": "_if"},
    "dual": {"dir": "unbounded", "suffix": "_ub"},
}


def column_names(mps_path):
    """Column names in file order, read straight from the MPS COLUMNS section."""
    names, seen, section = [], set(), None
    with gzip.open(mps_path, "rt", errors="replace") as f:
        for line in f:
            if not line.strip() or line.startswith("*"):
                continue
            if not line[0].isspace():
                section = line.split()[0]
                if section == "RHS":       # COLUMNS is over; stop reading
                    break
                continue
            if section != "COLUMNS" or "'MARKER'" in line:
                continue
            col = line.split()[0]
            if col not in seen:
                seen.add(col)
                names.append(col)
    return names


def rename_entry(entry, names):
    """Rewrite `x<index><op><value>` using the real column name."""
    m = ENTRY_RE.match(entry)
    if not m:
        return entry
    idx = int(m.group(1))
    if idx >= len(names):
        return entry
    return f"{names[idx]}{m.group(2)}{m.group(3)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "dataset")
    args = parser.parse_args()

    jobs = []
    for subset, info in SUBSETS.items():
        d = args.dataset_dir / info["dir"]
        if d.is_dir():
            jobs += [(subset, p) for p in sorted(d.glob(f"*{info['suffix']}.meta.json"))]
    print(f"resolving column names in {len(jobs)} sidecars", flush=True)

    t0 = time.time()
    for n, (subset, meta_path) in enumerate(jobs, 1):
        mps = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".mps.gz")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        names = column_names(mps)

        if subset == "primal":
            idx = meta.get("branch_var")
            if isinstance(idx, int) and idx < len(names):
                meta["branch_var_name"] = names[idx]
            meta["path_head_named"] = [rename_entry(e, names)
                                       for e in meta.get("path_entries", [])[:HEAD_LIMIT]]
            meta["path_entries_are_column_indices"] = True
        else:
            for drop in meta.get("drops", []):
                if drop.get("kind") == "bound":
                    j = drop.get("var")
                    if isinstance(j, int) and j < len(names):
                        drop["name"] = names[j]

        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        if n % 25 == 0 or n == len(jobs):
            print(f"  {n}/{len(jobs)}  ({time.time() - t0:.0f}s)", flush=True)

    print("done")


if __name__ == "__main__":
    main()
