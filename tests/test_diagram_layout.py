"""No text in a drawing may fall outside the drawing.

Twice now a label has been drawn past the edge of its own viewBox and been
quietly cut off: once "the search went here", once a long branch variable name
that also ran into its neighbour. Neither showed up in a test, because every
other test asks what the markup says, not where it lands.

Text extent cannot be measured without a font, so it is estimated. The
drawings set every label in the mono family at a size the stylesheet states,
and a monospaced advance is a fixed fraction of the size, so an estimate is
sound as long as it is generous. It is only ever used to prove there is room.
"""

import re
from dataclasses import replace

import pytest

from website import assets as A
from website import diagrams as D
from website.diagrams import provenance
from website.index import load_collection

# IBM Plex Mono advances 0.6em; the drawings are checked against a little more
# than that, so a label that only just fits still counts as fitting.
ADVANCE = 0.64

_TEXT = re.compile(r"<text([^>]*)>([^<]*)</text>")
_VIEWBOX = re.compile(r'viewBox="0 0 (\d+) (\d+)"')


def _font_size(classes: str) -> float:
    """The size the stylesheet sets for a label of these classes."""
    for name in ("lbl", "dim", "key", "tick", "axis-label"):
        if name in classes.split():
            found = re.search(
                rf"\.(?:prov|cloud) \.{re.escape(name)}\{{[^}}]*font-size:([\d.]+)px", A.SITE_CSS
            )
            assert found, f"no font-size for .{name}"
            return float(found.group(1))
    raise AssertionError(f"no known class in {classes!r}")


def _overflows(svg: str) -> list[str]:
    """Every label whose estimated box leaves the drawing."""
    box = _VIEWBOX.search(svg)
    assert box, "no viewBox"
    width = float(box.group(1))
    bad = []
    for attrs, text in (match.groups() for match in _TEXT.finditer(svg)):
        if not text.strip() or "transform=" in attrs:
            # a rotated label runs down the drawing rather than across it, and
            # this measures width; the axis title is the only one
            continue
        classes = re.search(r'class="([^"]*)"', attrs)
        x = float(re.search(r'\bx="(-?[\d.]+)"', attrs).group(1))
        anchor = re.search(r'text-anchor="(\w+)"', attrs)
        span = len(text) * ADVANCE * _font_size(classes.group(1) if classes else "")
        left = {"middle": x - span / 2, "end": x - span}.get(
            anchor.group(1) if anchor else "start", x
        )
        if left < 0 or left + span > width:
            bad.append(f"{text!r} spans {left:.0f}..{left + span:.0f} of {width:.0f}")
    return bad


@pytest.fixture(scope="module")
def samples():
    return load_collection("metadata/site-index.json")


def test_no_branch_diagram_writes_outside_its_own_drawing(samples):
    """Every published instance, including the fifty-four-character names."""
    for sample in samples:
        if sample.subset == "primal":
            assert not _overflows(D.branch_diagram(sample)), sample.instance


def test_no_drops_diagram_writes_outside_its_own_drawing(samples):
    """This one holds no text a reader supplied, which is the reason it has
    never overflowed. The guard is here so that stays true by test."""
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
    """Its axis labels and key are fixed text, but the frame moved once."""
    assert not _overflows(D.cloud(samples, page_rel="index.html"))
