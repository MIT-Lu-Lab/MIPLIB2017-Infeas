"""The three drawings the pages carry, as geometry rather than as pictures.

Each is a pure function returning SVG, so what is checked here is what the
markup claims: where a point lands, what it links to, and which numbers a
diagram states. Nothing renders an image to compare.
"""

import itertools
import math
import re
from dataclasses import replace
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from website import diagrams as D
from website.index import load_collection


def _dots(svg: str) -> list[str]:
    return re.findall(r"<a [^>]*>.*?</a>", svg, re.S)


def _marks(svg: str) -> list[str]:
    """The dot standing for the page being read, whatever else its class says."""
    return [value for value in re.findall(r'class="([^"]*)"', svg) if "here" in value.split()]


def _dual(index):
    return next(s for s in load_collection(index) if s.subset == "dual")


def _dropping(sample, *, bounds: int, rows: int):
    """The same instance with a known removal, head cleared to match."""
    return replace(
        sample,
        provenance=replace(sample.dual, bounds_dropped=bounds, rows_dropped=rows, drops_head=()),
    )


def _natural(sample):
    """The same instance as one whose relaxation needed no removals."""
    return replace(
        sample,
        provenance=replace(
            sample.dual, bounds_dropped=0, rows_dropped=0, natural_unbounded=True, drops_head=()
        ),
    )


def test_the_low_corner_and_the_high_corner_bound_the_plot():
    """Both axes share one range, so the extremes are the box's own corners."""
    low, high = D.LIMITS
    assert D.position(low, low) == (D.PAD_LEFT, D.PAD_TOP + D.PLOT)
    assert D.position(high, high) == (D.PAD_LEFT + D.PLOT, D.PAD_TOP)


def test_a_decade_is_the_same_distance_wherever_it_falls():
    """The map is logarithmic, which is the only reason the smallest instance
    and the largest can share one picture."""
    steps = [D.position(10**e, 1000)[0] for e in (2, 3, 4, 5)]
    gaps = [b - a for a, b in itertools.pairwise(steps)]
    assert max(gaps) - min(gaps) < 1e-9
    # and up is more constraints, not fewer
    assert D.position(1000, 10_000)[1] < D.position(1000, 1000)[1]


def test_a_shape_outside_the_range_lands_on_the_frame():
    """A drawing is not where a range error should first show up."""
    low, high = D.LIMITS
    x, y = D.position(low / 100, high * 100)
    assert x == D.PAD_LEFT and y == D.PAD_TOP
    assert D.radius(1) >= D.R_MIN


def test_mark_area_grows_with_the_nonzero_count():
    assert D.radius(10**5) < D.radius(10**6) < D.radius(10**7)


def test_every_instance_is_one_link_to_its_own_page(index):
    samples = load_collection(index)
    svg = D.cloud(samples, page_rel="index.html")
    links = re.findall(r'<a href="([^"]+)"', svg)
    assert links == [sample.page_path for sample in samples]
    assert len(_dots(svg)) == len(samples)


def test_a_link_resolves_from_the_page_that_carries_it(index):
    """The same cloud is drawn on the root and two directories down."""
    samples = load_collection(index)
    deep = D.cloud(samples, page_rel="primal-infeasible/aaa/index.html")
    assert f'<a href="../../{samples[0].page_path}"' in deep


def test_a_dot_names_the_instance_and_its_size(index):
    samples = load_collection(index)
    svg = D.cloud(samples, page_rel="index.html")
    sample = samples[0]
    assert f"<title>{sample.instance}" in svg
    assert f"{sample.n_vars:,}" in svg and f"{sample.n_cons:,}" in svg


def test_the_current_instance_is_marked_and_drawn_last(index):
    """Last, so the mark that matters is not buried under the cloud."""
    samples = load_collection(index)
    here = samples[-1]
    svg = D.cloud(samples, page_rel=here.page_path + "index.html", current=here)
    assert len(_marks(svg)) == 1
    marked = _dots(svg)[-1]
    assert here.instance in marked and _marks(marked)
    assert not _marks(D.cloud(samples, page_rel="index.html"))


def test_a_cloud_that_locates_one_instance_says_so(index):
    """The stylesheet greys the rest out from this class. Without it the two
    halves keep their colours and compete with the mark that matters."""
    samples = load_collection(index)
    locator = D.cloud(samples, page_rel="p/x/index.html", current=samples[0], linked=False)
    assert 'class="cloud locator"' in locator
    assert 'class="cloud"' in D.cloud(samples, page_rel="index.html")


def test_the_cloud_is_reachable_by_mouse_only(index):
    """Every dot repeats a row of a browse page, which is sortable, searchable
    and already reachable by keyboard. Three hundred extra tab stops buy
    nothing and cost the reader who has no mouse the most."""
    svg = D.cloud(load_collection(index), page_rel="index.html")
    assert svg.count('tabindex="-1"') == len(_dots(svg))


def test_the_branch_diagram_states_both_sides_of_the_split(index):
    """The published file is one side; naming only that side would leave the
    reader with no idea what the search did instead."""
    sample = next(s for s in load_collection(index) if s.subset == "primal")
    svg = D.branch_diagram(sample)
    branch = sample.primal
    published = int(branch.branch_value)
    taken, taken_value = D.taken_side(branch.branch_sense, published)
    # a branch splits an integer, so the sibling sits at the adjacent one
    assert taken_value == published - 1 or taken_value == published + 1
    # the drawing is XML, so these arrive escaped
    assert f"{branch.branch_label} {escape(branch.branch_sense)} {published}" in svg
    assert f"{branch.branch_label} {escape(taken)} {taken_value}" in svg
    assert str(branch.depth) in svg


def test_the_branch_diagram_does_not_draw_the_path_it_does_not_have(index):
    """path_head is the node's bound box, not the branches taken to reach it.
    Drawing twelve rungs would claim an order nothing recorded."""
    sample = next(s for s in load_collection(index) if s.subset == "primal")
    svg = D.branch_diagram(sample)
    for entry in sample.primal.path_head:
        assert entry not in svg


def test_the_drops_diagram_shows_the_change_of_state(index):
    """What the file is, not how much was taken: the counts are already the
    two lines of the panel it sits in."""
    sample = _dropping(_dual(index), bounds=51, rows=4)
    svg = D.drops_diagram(sample)
    assert ">bounded<" in svg and ">unbounded<" in svg
    assert "root relaxation" in svg and "this file" in svg
    assert "remove 51 bounds" in svg and "and 4 constraints" in svg


def test_the_drops_diagram_counts_in_the_singular(index):
    svg = D.drops_diagram(_dropping(_dual(index), bounds=1, rows=0))
    assert "remove 1 bound<" in svg
    assert "constraint" not in svg  # nothing was taken, so nothing is claimed


def test_a_relaxation_that_was_already_unbounded_shows_one_state(index):
    """There was no before: nothing turned it unbounded."""
    sample = next(s for s in load_collection(index) if s.subset == "dual")
    svg = D.drops_diagram(_natural(sample))
    assert svg.count("<rect") == 1
    assert "nothing was removed" in svg
    assert "arrow" not in svg and ">bounded<" not in svg


def test_every_drawing_is_well_formed_xml(index):
    samples = load_collection(index)
    drawings = [D.cloud(samples, page_rel="index.html")]
    for sample in samples:
        drawings.append(
            D.branch_diagram(sample) if sample.subset == "primal" else D.drops_diagram(sample)
        )
    drawings.append(D.drops_diagram(_natural(next(s for s in samples if s.subset == "dual"))))
    for svg in drawings:
        ElementTree.fromstring(svg)  # our own generated markup


def test_no_drawing_leaves_a_coordinate_at_full_float_precision(index):
    """Seventeen digits of a dot's centre is bytes on every page and precision
    no screen can show."""
    svg = D.cloud(load_collection(index), page_rel="index.html")
    for number in re.findall(r'(?:cx|cy)="([^"]+)"', svg):
        assert "." not in number or len(number.split(".")[-1]) <= 2
        assert math.isfinite(float(number))
