"""Re-read every published file and confirm it still has the status it claims.

    python -m scripts.verify_published [--dataset-dir dataset] [--jobs 4]

The dual-infeasible miner already re-read each MPS before publishing it; the
primal-infeasible miner never did. This closes that gap for the whole release:
each file is read back from disk, its LP relaxation is solved, and the status is
checked against the subset it was published under. The relaxation is what the
status rests on: an infeasible relaxation makes the program infeasible, and an
unbounded one makes a feasible program unbounded.

Verification uses HiGHS, not the CPLEX that produced the collection. A solver
confirming its own output proves little; an independent one confirming it is
evidence. HiGHS also needs no licence, so anyone can re-run this.

The dataset is read-only. The script writes a CSV report and exits non-zero if
anything fails.
"""

import argparse
import contextlib
import csv
import gzip
import hashlib
import importlib.metadata
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from scripts.dataset import DatasetEntry, DatasetError, scan_dataset
from scripts.release_contract import (
    VERIFICATION_ASSET_NAME,
    Manifest,
    load_manifest,
)
from website import DATASET_DIR
from website.domain import Subset

EXPECTED_STATUS: dict[Subset, str] = {"primal": "infeasible", "dual": "unbounded"}


@dataclass(frozen=True)
class SolveResult:
    """One structured solver outcome, before report formatting."""

    status: str | None = None
    read_warning: bool = False
    error: str | None = None
    other_status: str | None = None


@dataclass(frozen=True)
class CheckJob:
    """The complete, picklable input to one worker."""

    subset: Subset
    path: Path
    time_limit: float
    manifest_entry: tuple[int, str] | None = None


@dataclass(frozen=True)
class CheckRow:
    """One verification result before it crosses the CSV boundary."""

    subset: Subset
    file: str
    file_bytes: int
    sha256: str
    result: SolveResult
    manifest_entry: tuple[int, str] | None
    time_limit_seconds: float
    seconds: float

    @property
    def manifest_ok(self) -> bool | None:
        if self.manifest_entry is None:
            return None
        return (self.file_bytes, self.sha256) == self.manifest_entry

    @property
    def ok(self) -> bool:
        return (
            self.result.error is None
            and self.result.status == EXPECTED_STATUS[self.subset]
            and self.manifest_ok is not False
        )


def classify(mps_path: Path, time_limit: float) -> SolveResult:
    """Solve one published file's LP relaxation with a fresh HiGHS instance."""
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
            return SolveResult(error=f"readModel returned {status}")
        warned = status == highspy.HighsStatus.kWarning
        h.setOptionValue("solve_relaxation", True)
        h.run()
        ms = h.getModelStatus()
        S = highspy.HighsModelStatus
        if ms == S.kInfeasible:
            return SolveResult("infeasible", warned)
        if ms in (S.kUnbounded, S.kUnboundedOrInfeasible):
            # these were produced by relaxing a feasible problem, so the
            # ambiguous status resolves to unbounded
            return SolveResult("unbounded", warned)
        if ms == S.kOptimal:
            return SolveResult("optimal", warned)
        return SolveResult(read_warning=warned, other_status=h.modelStatusToString(ms))
    except Exception as exc:  # the report records whatever went wrong
        return SolveResult(error=str(exc))
    finally:
        h.clear()
        with contextlib.suppress(OSError):
            os.unlink(plain)


def _check(job: CheckJob) -> CheckRow:
    """Worker: fingerprint and classify one file, then time it."""
    t0 = time.time()
    # both: a solver result is only evidence about exact input bytes
    file_bytes = job.path.stat().st_size
    with job.path.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    result = classify(job.path, job.time_limit)
    return CheckRow(
        subset=job.subset,
        file=job.path.name,
        file_bytes=file_bytes,
        sha256=sha256,
        result=result,
        manifest_entry=job.manifest_entry,
        time_limit_seconds=job.time_limit,
        seconds=round(time.time() - t0, 1),
    )


def _result_text(result: SolveResult) -> str:
    """Format a structured solver result for the report and console."""
    if result.error is not None:
        return f"error:{result.error}"
    if result.status is None:
        return f"other:{result.other_status or 'unknown'}"
    warning = " (read warning)" if result.read_warning else ""
    return result.status + warning


def _csv_row(row: CheckRow, solver_version: str) -> dict[str, object]:
    """Convert one result at the CSV output boundary."""
    manifest_bytes, manifest_sha256 = row.manifest_entry or ("", "")
    return {
        "subset": row.subset,
        "file": row.file,
        "file_bytes": row.file_bytes,
        "sha256": row.sha256,
        "expected": EXPECTED_STATUS[row.subset],
        "got": _result_text(row.result),
        "manifest_bytes": manifest_bytes,
        "manifest_sha256": manifest_sha256,
        "manifest_ok": row.manifest_ok if row.manifest_ok is not None else "",
        "solver": "HiGHS",
        "solver_version": solver_version,
        "threads": 1,
        "time_limit_seconds": row.time_limit_seconds,
        "ok": row.ok,
        "seconds": row.seconds,
    }


def manifest_instances(
    manifest: Manifest, files: Sequence[DatasetEntry]
) -> dict[str, tuple[int, str]]:
    """Bind every local MPS, and only those files, to manifest ``instance`` rows."""
    declared = {
        item.name: (item.size, item.sha256)
        for item in manifest.artifacts
        if item.role == "instance"
    }
    local = {entry.mps.name for entry in files}
    missing = sorted(local - set(declared))
    extra = sorted(set(declared) - local)
    if missing or extra:
        details = []
        if missing:
            details.append(f"not in manifest: {', '.join(missing[:10])}")
        if extra:
            details.append(f"not in dataset: {', '.join(extra[:10])}")
        raise ValueError(
            "manifest instance inventory differs from the dataset; " + "; ".join(details)
        )
    return declared


def _highspy_version():
    try:
        return importlib.metadata.version("highspy")
    except importlib.metadata.PackageNotFoundError as exc:
        raise SystemExit(
            "cannot determine the HiGHS version; install highspy as a package"
        ) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(VERIFICATION_ASSET_NAME),
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="parallel solves; each holds one relaxation in memory, and the "
        "largest published file is 362 MB, so keep this modest",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=900.0,
        help="seconds per file; a file that runs out reports "
        "other:... rather than silently passing",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="optional release manifest binding every solve to exact input bytes",
    )
    args = parser.parse_args()

    try:
        files = scan_dataset(args.dataset_dir)
    except DatasetError as exc:
        raise SystemExit(str(exc)) from exc
    if not files:
        raise SystemExit(f"{args.dataset_dir}: no published files found")
    contract = {}
    if args.manifest:
        try:
            contract = manifest_instances(load_manifest(args.manifest), files)
        except ValueError as exc:
            raise SystemExit(f"{args.manifest}: {exc}") from exc
    solver_version = _highspy_version()
    jobs = [
        CheckJob(entry.subset, entry.mps, args.time_limit, contract.get(entry.mps.name))
        for entry in files
    ]
    binding = f", bound to {args.manifest}" if args.manifest else ""
    print(f"verifying {len(jobs)} files with {args.jobs} HiGHS {solver_version} worker(s){binding}")

    # results stream to the report as they land, so a run that is interrupted
    # still leaves everything it managed to check
    fields = [
        "subset",
        "file",
        "file_bytes",
        "sha256",
        "expected",
        "got",
        "manifest_bytes",
        "manifest_sha256",
        "manifest_ok",
        "solver",
        "solver_version",
        "threads",
        "time_limit_seconds",
        "ok",
        "seconds",
    ]
    by_subset = {}
    failures = 0
    done = 0
    t0 = time.time()
    with args.report.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(_check, job) for job in jobs]
            for fut in as_completed(futures):
                row = fut.result()
                got = _result_text(row.result)
                writer.writerow(_csv_row(row, solver_version))
                out.flush()
                done += 1
                mark = "ok  " if row.ok else "FAIL"
                print(
                    f"  [{done:>3d}/{len(jobs)}] {mark} {row.file:<44s} "
                    f"{got:<12s} {row.seconds:>7.1f}s "
                    f"(elapsed {(time.time() - t0) / 60:.0f}m)",
                    flush=True,
                )
                if not row.ok:
                    failures += 1
                summary = by_subset.setdefault(row.subset, {"n": 0, "ok": 0})
                summary["n"] += 1
                summary["ok"] += row.ok
    print()
    for subset, d in sorted(by_subset.items()):
        print(f"  {subset:<7s} {d['ok']}/{d['n']} confirmed {EXPECTED_STATUS[subset]}")
    print(f"\nreport written to {args.report}")

    if failures:
        print(f"\n{failures} file(s) did not verify")
        return 1
    print("\nall published files verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
