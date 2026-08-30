"""The nonzero pattern: what it counts, and what its file says it is.

The drawing is a raster, so unlike the other figures it cannot be read back out
of the page. What is checked here is the grid it comes from and the header of
the file it is written to.
"""

import gzip
import struct
import zlib

import pytest

from scripts import build_patterns as P

# Four constraints and four columns, one entry on each diagonal position, plus
# an objective row that is not a constraint and must not be counted as one.
TINY = """NAME          tiny
ROWS
 N  obj
 L  r1
 L  r2
 L  r3
 L  r4
COLUMNS
    c1  obj  1.0  r1  1.0
    c2  r2  1.0
    c3  r3  1.0
    c4  r4  1.0
RHS
    rhs  r1  1.0
ENDATA
"""


@pytest.fixture
def tiny(tmp_path):
    path = tmp_path / "tiny.mps.gz"
    path.write_bytes(gzip.compress(TINY.encode()))
    return path


def test_the_objective_row_is_not_a_constraint(tiny):
    """The published row count excludes it, so the grid has to as well, or the
    drawing is of a matrix one row taller than the one described beside it."""
    _, n_vars, n_cons = P.counts(tiny, size=4)
    assert (n_vars, n_cons) == (4, 4)


def test_each_entry_lands_in_its_own_cell(tiny):
    """Four entries on the diagonal of a four by four grid."""
    grid, _, _ = P.counts(tiny, size=4)
    assert [i for i, n in enumerate(grid) if n] == [0, 5, 10, 15]
    assert sum(grid) == 4  # the objective entry is not one of them


def test_a_grid_coarser_than_the_matrix_gathers_entries(tiny):
    """This is the whole point at scale: one cell of a large instance covers a
    hundred thousand rows, and what it reports is how many landed there."""
    grid, _, _ = P.counts(tiny, size=2)
    assert grid == [2, 0, 0, 2]


def test_ink_is_logarithmic_and_an_occupied_cell_is_never_blank():
    """A single nonzero in a cell covering ten billion positions is still a
    fact; at alpha zero it would read as emptiness."""
    values = P.alpha([0, 1, 10, 1000])
    assert values[0] == 0
    assert values[1] >= P.FLOOR
    assert values[1] < values[2] < values[3] == 255


def test_an_empty_grid_is_transparent_rather_than_a_division_by_zero():
    assert set(P.alpha([0, 0, 0, 0])) == {0}


def test_the_file_says_it_is_greyscale_with_alpha():
    """The page masks with the alpha channel. A colour type that carries no
    alpha would mask nothing and the card would come out a solid square."""
    data = P.png(bytes(range(16)), size=4)
    assert data[:8] == bytes((137, 80, 78, 71, 13, 10, 26, 10))  # the PNG signature
    width, height, depth, colour = struct.unpack(">IIBB", data[16:26])
    assert (width, height, depth, colour) == (4, 4, 8, 4)


def test_the_pixels_survive_the_round_trip():
    """Two bytes a pixel, black throughout, and a filter byte on each row."""
    values = bytes(range(16))
    data = P.png(values, size=4)
    start = data.index(b"IDAT") + 4
    length = struct.unpack(">I", data[start - 8 : start - 4])[0]
    raw = zlib.decompress(data[start : start + length])
    assert len(raw) == 4 * (1 + 2 * 4)
    for row in range(4):
        line = raw[row * 9 : (row + 1) * 9]
        assert line[0] == 0  # no filter
        assert set(line[1::2]) == {0}  # grey stays black
        assert line[2::2] == values[row * 4 : (row + 1) * 4]
