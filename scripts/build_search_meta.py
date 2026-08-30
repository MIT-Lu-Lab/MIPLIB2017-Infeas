"""Record how much search produced each primal-infeasible file.

    python -m scripts.build_search_meta --run-log ../miplib-infeas/run_log_infeas.csv

An instance page states the depth of the node it holds. Depth says where the
node sits, not how much searching found it: a tree of depth n holds up to 2^n
nodes, and two instances at the same depth can come from runs that differ by
orders of magnitude in work. The node count is the second number, and it is
the mining run's, not the published file's.

The log the miners write is a CSV of one row per source instance, and it is
not part of this repository: its columns are theirs to change. What is kept
here is the one column the site states, as JSON, keyed by instance, in the
shape the MIPLIB metadata cache already uses.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from website import INDEX_FILE, ROOT
from website.index import load_collection

DEFAULT_OUT = ROOT / "metadata" / "search_meta.json"


def nodes_by_instance(run_log: Path, instances: set[str]) -> dict[str, dict[str, int]]:
    """The node count for each published instance, read from the miners' log.

    A missing row raises, which is the whole check: the log has to be the run
    that produced the collection, and one that is not will not cover it.
    """

    with run_log.open(encoding="utf-8", newline="") as handle:
        rows = {row["source_instance"]: row for row in csv.DictReader(handle)}
    return {name: {"nodes": int(rows[name]["nodes"])} for name in sorted(instances)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=INDEX_FILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    instances = {s.instance for s in load_collection(args.index) if s.subset == "primal"}
    try:
        found = nodes_by_instance(args.run_log, instances)
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"{args.run_log}: {exc}, so it is not the run that produced them") from exc

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(found, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(found)} entries to {args.out}")


if __name__ == "__main__":
    main()
