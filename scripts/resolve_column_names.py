"""Resolve the column indices in each sidecar to the real MPS column names.

    python -m scripts.resolve_column_names [--dataset-dir dataset]

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
import re
import time
from pathlib import Path

from scripts.dataset import DatasetError, read_entry_sidecar, replace_sidecar, scan_dataset
from website import DATASET_DIR
from website.domain import HEAD_LIMIT

ENTRY_RE = re.compile(r"^x(\d+)(<=|>=)(.+)$")


def column_names(mps_path):
    """Column names in file order, read straight from the MPS COLUMNS section."""
    names, seen, section = [], set(), None
    with gzip.open(mps_path, "rt", errors="replace") as f:
        for line in f:
            if not line.strip() or line.startswith("*"):
                continue
            if not line[0].isspace():
                section = line.split()[0]
                if section == "RHS":  # COLUMNS is over; stop reading
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
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    args = parser.parse_args()

    try:
        dataset = scan_dataset(args.dataset_dir)
    except DatasetError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"resolving column names in {len(dataset)} sidecars", flush=True)

    t0 = time.time()
    for n, entry in enumerate(dataset, 1):
        try:
            meta = read_entry_sidecar(entry)
        except DatasetError as exc:
            raise SystemExit(str(exc)) from exc
        names = column_names(entry.mps)

        if entry.subset == "primal":
            idx = meta.get("branch_var")
            if type(idx) is int and 0 <= idx < len(names):
                meta["branch_var_name"] = names[idx]
            meta["path_head_named"] = [
                rename_entry(e, names) for e in meta.get("path_entries", [])[:HEAD_LIMIT]
            ]
            meta["path_entries_are_column_indices"] = True
        else:
            for drop in meta.get("drops", []):
                if drop.get("kind") == "bound":
                    j = drop.get("var")
                    if type(j) is int and 0 <= j < len(names):
                        drop["name"] = names[j]

        replace_sidecar(entry.sidecar, meta)
        if n % 25 == 0 or n == len(dataset):
            print(f"  {n}/{len(dataset)}  ({time.time() - t0:.0f}s)", flush=True)

    print("done; next: python -m scripts.build_site_index")


if __name__ == "__main__":
    main()
