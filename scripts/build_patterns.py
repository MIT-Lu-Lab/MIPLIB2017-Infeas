"""Draw each published instance's nonzero density, once, into a committed PNG.

    python -m scripts.build_patterns --dataset-dir ../miplib-infeas/dataset

A spy plot of these matrices cannot be drawn at size: the largest is 20,682,487
columns by 19,912,111 rows. What is drawn instead is a fixed grid over the
matrix, each cell carrying how many nonzeros fall inside it. Occupancy alone
would be useless at this scale, because a cell of a large instance covers a
hundred thousand rows and a hundred thousand columns and almost always holds
something: every big instance would come out a solid block.

The image is greyscale-with-alpha, and only the alpha channel carries the
value. The page uses it as a CSS mask, so the colour comes from the same
stylesheet token as everything else and the printed page gets it in ink rather
than in the dark palette. That is what lets a raster live on a site whose other
drawings are markup.

Nothing at build time reads a matrix: this writes patterns/, the build copies
it, and the pages point at it.
"""

from __future__ import annotations

import argparse
import gzip
import math
import struct
import sys
import zlib
from pathlib import Path

from scripts.dataset import DatasetError, scan_dataset
from website import DATASET_DIR, ROOT

# Cells on a side. At 128 the file is a kilobyte or two and the structure a
# reader can see at 200 pixels wide is still there.
SIZE = 128

# The faintest a cell holding anything may be drawn. A single nonzero in a cell
# covering ten billion positions is still a fact about the matrix, and at alpha
# 0 it would be indistinguishable from emptiness.
FLOOR = 52


class PatternError(ValueError):
    """A published file is not the MPS this expects."""


def _sections(path: Path):
    """Yield (section, fields) for every data line of an MPS file."""

    section = ""
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("*"):
                continue
            if not line[0].isspace():
                section = line.split()[0].upper()
                continue
            yield section, line.split()


def _shape(path: Path) -> tuple[dict[str, int], int]:
    """The constraint rows in file order, and how many columns follow them.

    Columns are counted rather than collected: COLUMNS groups every entry of a
    column together, so a change of name is a new one. The largest instance has
    twenty million of them, and their names are not needed twice.
    """

    rows: dict[str, int] = {}
    columns, seen = 0, ""
    for section, fields in _sections(path):
        if section == "ROWS":
            # the objective is a free row, not a constraint, and the published
            # counts do not include it
            if fields[0].upper() != "N":
                rows.setdefault(fields[1], len(rows))
        elif section == "COLUMNS":
            if "MARKER" not in fields and fields[0] != seen:
                seen = fields[0]
                columns += 1
        elif section == "RHS":
            break
    return rows, columns


def counts(path: Path, size: int = SIZE) -> tuple[list[int], int, int]:
    """Nonzeros per cell of a size x size grid over one instance's matrix.

    Read in two passes. A cell's column depends on how many columns there
    turn out to be, which is only known once COLUMNS has been read to the end;
    holding every entry until then meant a list of fifty-eight million tuples
    on the largest instance, several gigabytes to save one decompression.

    Returns the grid, the column count and the row count, all read from the
    file rather than from the index, so the drawing cannot disagree with the
    matrix it describes.
    """

    rows, n_vars = _shape(path)
    n_cons = len(rows)
    if not n_cons or not n_vars:
        raise PatternError(f"{path}: no ROWS or no COLUMNS section")

    grid = [0] * (size * size)
    column = -1
    seen = ""
    for section, fields in _sections(path):
        if section != "COLUMNS":
            if section == "RHS":
                break
            continue
        if "MARKER" in fields:
            continue
        if fields[0] != seen:
            seen = fields[0]
            column += 1
        band = column * size // n_vars
        for index in range(1, len(fields) - 1, 2):
            row = rows.get(fields[index])
            if row is None:  # an entry in the objective row
                continue
            grid[(row * size // n_cons) * size + band] += 1
    return grid, n_vars, n_cons


def alpha(grid: list[int]) -> bytes:
    """Map cell counts onto ink, logarithmically.

    Density spans orders of magnitude inside one matrix as much as across the
    collection, so a linear map leaves everything but the densest cell blank.
    """

    peak = max(grid)
    if not peak:
        return bytes(len(grid))
    scale = (255 - FLOOR) / math.log1p(peak)
    return bytes(0 if n == 0 else FLOOR + round(scale * math.log1p(n)) for n in grid)


def png(values: bytes, size: int = SIZE) -> bytes:
    """An 8-bit greyscale-with-alpha PNG whose colour is black throughout.

    Written here rather than with an imaging library so that this script needs
    nothing outside the standard library, and so the repository's type check
    does not have to resolve an import CI never installs.
    """

    scanlines = []
    for row in range(size):
        line = bytearray()
        for value in values[row * size : (row + 1) * size]:
            line += b"\x00" + bytes((value,))
        scanlines.append(b"\x00" + bytes(line))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 4, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(scanlines), 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "patterns")
    parser.add_argument("--only", help="one instance name, for a quick look")
    args = parser.parse_args()

    try:
        entries = scan_dataset(args.dataset_dir)
    except DatasetError as exc:
        raise SystemExit(str(exc)) from exc
    if args.only:
        entries = tuple(entry for entry in entries if entry.instance == args.only)
        if not entries:
            raise SystemExit(f"{args.only}: not in {args.dataset_dir}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for entry in entries:
        grid, n_vars, n_cons = counts(entry.mps)
        (args.out_dir / f"{entry.stem}.png").write_bytes(png(alpha(grid)))
        written += 1
        print(f"{written:>4}/{len(entries)} {entry.stem} {n_vars}x{n_cons}", file=sys.stderr)
    print(f"wrote {written} patterns to {args.out_dir}")


if __name__ == "__main__":
    main()
