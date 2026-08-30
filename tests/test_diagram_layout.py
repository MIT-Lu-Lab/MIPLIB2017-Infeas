"""No text in a drawing may fall outside the drawing.

Twice a label has been drawn past the edge of its own viewBox and quietly cut
off: once "the search went here", once a long branch variable name that ran
into its neighbour as well. Neither showed up in a test, because every other
test asks what the markup says, not where it lands.

Text extent cannot be measured without a font, so it is estimated. Every label
is set in the mono family, whose advance is 0.6em, at a size and an alignment
the stylesheet states rather than the markup, so both are read from there. The
estimate is deliberately generous: it is only ever used to prove there is room.
"""

import re
from dataclasses import replace

import pytest

from website import assets as A
from website import diagrams as D
from website.diagrams import provenance
from website.index import load_collection

# A little over the 0.6em the font actually advances, so a label that only just
# fits still counts as fitting.
ADVANCE = 0.64

_TEXT = re.compile(r"<text([^>]*)>(.*?)</text>", re.S)
_TAG = re.compile(r"<[^>]*>")
_VIEWBOX = re.compile(r'viewBox="0 0 (\d+) (\d+)"')

# Which rule styles a label, least specific first. A drawing sets these classes
# and the stylesheet sets the size and the alignment, so a change to either is
# something this reads rather than something it has to be told.
SELECTORS = (
    ({"lbl"}, r"\.prov \.lbl"),
    ({"dim"}, r"\.prov \.dim"),
    ({"tick"}, r"\.cloud \.tick"),
    ({"tick", "x"}, r"\.cloud \.tick\.x"),
    ({"tick", "y"}, r"\.cloud \.tick\.y"),
    ({"axis-label"}, r"\.cloud \.axis-label"),
    ({"key"}, r"\.cloud \.key"),
    ({"key", "dim"}, r"\.cloud \.key\.dim"),
)


def _declared(classes: set[str], prop: str) -> str | None:
    """What the stylesheet sets for this property on a label of these classes.

    The most specific matching rule wins, as it does in a browser: a size set
    on .key and narrowed on .key.dim resolves the way the page renders it.
    """
    found = None
    for names, selector in SELECTORS:
        if not names <= classes:
            continue
        match = re.search(rf"{selector}\{{[^}}]*{prop}:([^;}}]+)", A.SITE_CSS)
        if match:
            found = match.group(1).strip()
    return found


def _overflows(svg: str) -> list[str]:
    """Every label whose estimated box leaves the drawing."""
    box = _VIEWBOX.search(svg)
    assert box, "no viewBox"
    width = float(box.group(1))
    bad = []
    for attrs, inner in (match.groups() for match in _TEXT.finditer(svg)):
        # a label may hold a tspan, as every power of ten does
        text = _TAG.sub("", inner)
        if not text.strip() or "transform=" in attrs:
            # a rotated label runs down the drawing rather than across it, and
            # this measures width; the axis title is the only one
            continue
        classes = set(re.search(r'class="([^"]*)"', attrs).group(1).split())
        size = _declared(classes, "font-size")
        assert size, f"no font-size for {sorted(classes)}"
        anchor = re.search(r'text-anchor="(\w+)"', attrs)
        align = anchor.group(1) if anchor else _declared(classes, "text-anchor") or "start"
        x = float(re.search(r'\bx="(-?[\d.]+)"', attrs).group(1))
        span = len(text) * ADVANCE * float(size.removesuffix("px"))
        left = {"middle": x - span / 2, "end": x - span}.get(align, x)
        if left < 0 or left + span > width:
            bad.append(f"{text!r} spans {left:.0f}..{left + span:.0f} of {width:.0f}")
    return bad


@pytest.fixture(scope="module")
def samples():
    # with the search metadata: without it every node count is None and the
    # widest label in the branch drawing is never measured at all
    return load_collection("metadata/site-index.json", search_path="metadata/search_meta.json")


def test_the_check_reads_every_label_including_the_powers_of_ten(samples):
    """A tick label holds a tspan. Skipping those left this checking four of
    the cloud's twenty labels while reporting that all of them fit."""
    svg = D.cloud(samples, page_rel="index.html")
    assert sum(1 for _ in _TEXT.finditer(svg)) == 20
    # the sizes and alignments come from the stylesheet, not from the markup
    assert _declared({"key", "dim"}, "font-size") == "24px"  # not .prov .dim's 16px
    assert _declared({"tick", "y"}, "text-anchor") == "end"


def test_no_branch_diagram_writes_outside_its_own_drawing(samples):
    """Every published instance, including the fifty-four-character names."""
    for sample in samples:
        if sample.subset == "primal":
            assert not _overflows(D.branch_diagram(sample)), sample.instance


def test_no_drops_diagram_writes_outside_its_own_drawing(samples):
    """This one holds no text a reader supplied, which is why it has never
    overflowed. The guard is here so that stays true by test."""
    for sample in samples:
        if sample.subset == "dual":
            assert not _overflows(D.drops_diagram(sample))
    natural = next(s for s in samples if s.subset == "dual")
    assert not _overflows(
        D.drops_diagram(
            replace(
                natural,
                provenance=replace(
                    natural.dual,
                    bounds_dropped=0,
                    rows_dropped=0,
                    natural_unbounded=True,
                    drops_head=(),
                    rounds=0,
                ),
            )
        )
    )


def test_a_name_at_the_limit_still_fits(samples):
    """The cut is what keeps the line inside; this is where it is checked."""
    sample = next(s for s in samples if s.subset == "primal")
    at_limit = replace(
        sample, provenance=replace(sample.primal, branch_var_name="W" * provenance.NAME_LIMIT)
    )
    assert not _overflows(D.branch_diagram(at_limit))


def test_the_cloud_keeps_its_labels_inside(samples):
    """Its axis labels and key are fixed text, but the frame has moved once."""
    assert not _overflows(D.cloud(samples, page_rel="index.html"))
