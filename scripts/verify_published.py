"""Re-read every published file and confirm it still has the status it claims.

    python scripts/verify_published.py [--dataset-dir dataset] [--jobs 4]

The dual-infeasible miner already re-read each MPS before publishing it; the
primal-infeasible miner never did. This closes that gap for the whole release:
each file is read back from disk as an LP and solved, and the status is checked
against the subset it was published under.

Verification uses HiGHS, not the CPLEX that produced the collection. A solver
confirming its own output proves little; an independent one confirming it is
evidence. HiGHS also needs no licence, so anyone can re-run this.

Reads only. Writes a CSV report and exits non-zero if anything fails.
"""

import argparse
import contextlib
import csv
import gzip
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# published layout: dataset/<dir>/<instance>_<suffix>.mps.gz
SUBSETS = {
    "primal": {"dir": "infeasible", "suffix": "_if", "want": "infeasible"},
    "dual": {"dir": "unbounded", "suffix": "_ub", "want": "unbounded"},
}


def classify(mps_path, time_limit):
    """Solve one published file as an LP and report what HiGHS makes of it.

    Returns one of 'infeasible', 'unbounded', 'optimal', 'other:<status>', or
    'error:<message>'. A fresh Highs object per call keeps workers independent.
    """
    # highspy comes with a licensed HiGHS install rather than from PyPI alone, and
    # nothing else in the repository needs a solver, so CI has none to resolve it
    # against. The import is local for the same reason: importing this module
    # must not require one.
    import highspy  # pyright: ignore[reportMissingImports]

    # HiGHS cannot read gzipped MPS, so decompress to a scratch file first.
    # The largest published file is 362 MB compressed, so this is deliberately
    # streamed and deleted immediately after the solve.
    fd, plain = tempfile.mkstemp(suffix=".mps")
    os.close(fd)
    h = highspy.Highs()
    try:
        with gzip.GzipFile(mps_path, "rb") as src, open(plain, "wb") as dst:
            shutil.copyfileobj(src, dst, length=4 << 20)
        h.silent()
        h.setOptionValue("threads", 1)
        h.setOptionValue("time_limit", float(time_limit))
        status = h.readModel(plain)
        # kWarning means the model was read but something was flagged, most often
        # matrix coefficients at or below 1e-9 that HiGHS drops. That is a real
        # property of the instance, not a read failure, so the solve proceeds.
        if status not in (highspy.HighsStatus.kOk, highspy.HighsStatus.kWarning):
            return f"error:readModel returned {status}"
        warned = status == highspy.HighsStatus.kWarning
        h.run()
        ms = h.getModelStatus()
        S = highspy.HighsModelStatus
        suffix = " (read warning)" if warned else ""
        if ms == S.kInfeasible:
            return "infeasible" + suffix
        if ms in (S.kUnbounded, S.kUnboundedOrInfeasible):
            # these were produced by relaxing a feasible problem, so the
            # ambiguous status resolves to unbounded
            return "unbounded" + suffix
        if ms == S.kOptimal:
            return "optimal" + suffix
        return f"other:{h.modelStatusToString(ms)}"
    except Exception as exc:  # the report records whatever went wrong
        return f"error:{exc}"
    finally:
        h.clear()
        with contextlib.suppress(OSError):
            os.unlink(plain)


def _check(args):
    """Worker: classify one file and time it."""
    subset, path_str, time_limit = args
    path = Path(path_str)
    t0 = time.time()
    got = classify(path, time_limit)
    return {
        "subset": subset,
        "file": path.name,
        "expected": SUBSETS[subset]["want"],
        "got": got,
        "ok": got.split(" (")[0] == SUBSETS[subset]["want"],
        "seconds": round(time.time() - t0, 1),
    }


def collect(dataset_dir):
    """Every published .mps.gz, paired with the subset it was published under."""
    jobs = []
    for subset, info in SUBSETS.items():
        subdir = dataset_dir / info["dir"]
        if not subdir.is_dir():
            continue
        for p in sorted(subdir.glob(f"*{info['suffix']}.mps.gz")):
            jobs.append((subset, str(p)))
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "dataset")
    parser.add_argument("--report", type=Path, default=Path("verify_published.csv"))
    parser.add_argument("--jobs", type=int, default=4,
                        help="parallel solves; each holds one LP in memory, and the "
                             "largest published file is 362 MB, so keep this modest")
    parser.add_argument("--time-limit", type=float, default=900.0,
                        help="seconds per file; a file that runs out reports "
                             "other:... rather than silently passing")
    args = parser.parse_args()

    jobs = [(s, p, args.time_limit) for s, p in collect(args.dataset_dir)]
    if not jobs:
        raise SystemExit(f"{args.dataset_dir}: no published files found")
    print(f"verifying {len(jobs)} files with {args.jobs} HiGHS worker(s)")

    # results stream to the report as they land, so a run that is interrupted
    # still leaves everything it managed to check
    fields = ["subset", "file", "expected", "got", "ok", "seconds"]
    rows, failures = [], []
    done = 0
    t0 = time.time()
    with args.report.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = {pool.submit(_check, j): j for j in jobs}
            for fut in as_completed(futures):
                row = fut.result()
                rows.append(row)
                writer.writerow(row)
                out.flush()
                done += 1
                mark = "ok  " if row["ok"] else "FAIL"
                print(f"  [{done:>3d}/{len(jobs)}] {mark} {row['file']:<44s} "
                      f"{row['got']:<12s} {row['seconds']:>7.1f}s "
                      f"(elapsed {(time.time() - t0) / 60:.0f}m)", flush=True)
                if not row["ok"]:
                    failures.append(row)

    by_subset = {}
    for r in rows:
        d = by_subset.setdefault(r["subset"], {"n": 0, "ok": 0})
        d["n"] += 1
        d["ok"] += bool(r["ok"])
    print()
    for subset, d in sorted(by_subset.items()):
        print(f"  {subset:<7s} {d['ok']}/{d['n']} confirmed {SUBSETS[subset]['want']}")
    print(f"\nreport written to {args.report}")

    if failures:
        print(f"\n{len(failures)} file(s) did not verify")
        return 1
    print("\nall published files verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
