"""The drawings a page carries, as SVG built from the index it already has.

Three of them: the cloud of every published instance, which the overview shows
whole and an instance page shows with its own dot marked; and, on an instance
page, the branch behind a primal-infeasible file or the removals behind a
dual-infeasible one.

They are written here rather than drawn by a plotting library because the
markup has to do things a picture cannot. A dot is a link to the instance it
stands for. Every colour is a stylesheet token, so one drawing serves the dark
page and the light one a printer gets, with no second file. And the whole cloud
is about three kilobytes of repeated markup, against three hundred for the same
scatter rendered to an image.

Every drawing leaves here as Markup, so the templates that place them need no
`| safe` and cannot forget one. Everything variable inside is escaped where it
is written: text through escape(), attributes through quoteattr().
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from xml.sax.saxutils import escape, quoteattr

from markupsafe import Markup

from .content import fmt_int
from .domain import Sample
from .urls import rel

# One range for both axes, wide enough for the smallest constraint count and
# the largest variable count in the collection, rounded outwards to leave the
# extremes off the frame.
LIMITS = (18.0, 4.0e7)

# The plot is square in user units: a decade is the same distance either way,
# whatever width the page gives the drawing. The padding holds the tick labels.
PLOT = 1000.0
PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 108.0, 18.0, 18.0, 84.0
WIDTH = PAD_LEFT + PLOT + PAD_RIGHT
HEIGHT = PAD_TOP + PLOT + PAD_BOTTOM

# Decade gridlines, the ones that fall inside LIMITS.
DECADES = tuple(10**e for e in range(2, 8))

# A dot's radius over the collection's nonzero range. A published instance has
# at least 10^5 nonzeros and the largest has under 10^8, so the span is under
# three decades. What catches the pointer is a fat transparent stroke set in
# the stylesheet, which costs no markup at all.
NZ_REF, R_BASE, R_PER_DECADE, R_MIN = 5.0, 7.0, 3.2, 3.0


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def position(n_vars: int | float, n_cons: int | float) -> tuple[float, float]:
    """Where an instance of this shape sits, in user units.

    Clamped to the frame. Nothing published falls outside LIMITS, but a drawing
    is not the place to discover that: a point beyond the range belongs on the
    edge of the picture rather than loose on the page.
    """

    lo, hi = (math.log10(limit) for limit in LIMITS)
    span = hi - lo
    x = PAD_LEFT + (math.log10(n_vars) - lo) / span * PLOT
    y = PAD_TOP + PLOT - (math.log10(n_cons) - lo) / span * PLOT
    return _clamp(x, PAD_LEFT, PAD_LEFT + PLOT), _clamp(y, PAD_TOP, PAD_TOP + PLOT)


def radius(nnz: int) -> float:
    """A dot's radius, growing with the decade of its nonzero count."""

    return max(R_MIN, R_BASE + R_PER_DECADE * (math.log10(nnz) - NZ_REF))


def _n(value: float) -> str:
    """A coordinate at the precision a screen can show, and no more.

    The plot is a thousand units across and renders around five hundred
    pixels wide, so a whole unit is half a pixel. Decimals here would be two
    bytes each on every dot of every page, buying nothing anyone can see.
    """

    return str(round(value))


def _frame() -> list[str]:
    """The box and its decade ticks, drawn under everything else."""

    parts = [
        f'<rect class="frame" x="{_n(PAD_LEFT)}" y="{_n(PAD_TOP)}"'
        f' width="{_n(PLOT)}" height="{_n(PLOT)}"/>'
    ]
    for decade in DECADES:
        x, y = position(decade, decade)
        exponent = int(math.log10(decade))
        parts.append(
            f'<line class="grid" x1="{_n(x)}" y1="{_n(PAD_TOP)}"'
            f' x2="{_n(x)}" y2="{_n(PAD_TOP + PLOT)}"/>'
        )
        parts.append(
            f'<line class="grid" x1="{_n(PAD_LEFT)}" y1="{_n(y)}"'
            f' x2="{_n(PAD_LEFT + PLOT)}" y2="{_n(y)}"/>'
        )
        parts.append(
            f'<text class="tick x" x="{_n(x)}" y="{_n(PAD_TOP + PLOT + 46)}">'
            f"10<tspan class=\"exp\" dy='-14'>{exponent}</tspan></text>"
        )
        parts.append(
            f'<text class="tick y" x="{_n(PAD_LEFT - 20)}" y="{_n(y + 12)}">'
            f"10<tspan class=\"exp\" dy='-14'>{exponent}</tspan></text>"
        )
    parts.append(
        f'<text class="axis-label x" x="{_n(PAD_LEFT + PLOT / 2)}"'
        f' y="{_n(HEIGHT - 8)}"># variables</text>'
    )
    parts.append(
        f'<text class="axis-label y" x="{_n(-(PAD_TOP + PLOT / 2))}" y="30"'
        f' transform="rotate(-90)"># constraints</text>'
    )
    return parts


# The key sits inside the frame: identity at the top left, where the cloud is
# thin, and the size scale at the bottom right, where nothing lands because an
# instance with few constraints and many variables is not a shape MIPLIB holds.
_KEY_X, _KEY_Y, _KEY_STEP = 168.0, 76.0, 46.0
_SIZE_X, _SIZE_Y, _SIZE_STEP = 1046.0, 852.0, 62.0


def _legend(samples: Sequence[Sample]) -> list[str]:
    """Which colour is which half, and what a dot's size means."""

    counts = {
        "primal": sum(1 for s in samples if s.subset == "primal"),
        "dual": sum(1 for s in samples if s.subset == "dual"),
    }
    parts = []
    for row, (subset, tone, label) in enumerate(
        (("primal", "p", "Infeasible"), ("dual", "d", "Unbounded"))
    ):
        y = _KEY_Y + row * _KEY_STEP
        # grouped, so the filter that hides one half hides its key with it
        parts.append(
            f'<g class="key-{tone}">'
            f'<circle class="{tone}" cx="{_n(_KEY_X)}" cy="{_n(y)}" r="9"/>'
            f'<text class="key" x="{_n(_KEY_X + 24)}" y="{_n(y + 10)}">'
            f"{label} ({fmt_int(counts[subset])})</text></g>"
        )
    parts.append(
        f'<text class="key dim" x="{_n(_SIZE_X)}" y="{_n(_SIZE_Y - 34)}" text-anchor="end">'
        "nonzeros</text>"
    )
    for row, exponent in enumerate((5, 6, 7)):
        y = _SIZE_Y + row * _SIZE_STEP
        parts.append(
            f'<circle class="key-dot" cx="{_n(_SIZE_X)}" cy="{_n(y)}"'
            f' r="{_n(radius(10**exponent))}"/>'
        )
        parts.append(
            f'<text class="key dim" x="{_n(_SIZE_X - 26)}" y="{_n(y + 9)}" text-anchor="end">'
            f"10<tspan class=\"exp\" dy='-11'>{exponent}</tspan></text>"
        )
    return parts


def _dot(sample: Sample, page_rel: str, here: bool, linked: bool) -> str:
    x, y = position(sample.n_vars, sample.n_cons)
    tone = "p" if sample.subset == "primal" else "d"
    classes = f"{tone} here" if here else tone
    mark = (
        f'<circle class={quoteattr(classes)} cx="{_n(x)}" cy="{_n(y)}"'
        f' r="{_n(radius(sample.nnz))}"/>'
    )
    if not linked and not here:
        return mark
    label = (
        f"{sample.instance}: {fmt_int(sample.n_vars)} × "
        f"{fmt_int(sample.n_cons)}, {fmt_int(sample.nnz)} nonzeros"
    )
    title = f"<title>{escape(label)}</title>"
    if not linked:
        return f"<g>{title}{mark}</g>"
    return (
        # tabindex=-1: every dot repeats a row of a browse page, which is
        # searchable, sortable and already reachable by keyboard.
        f'<a href={quoteattr(rel(page_rel, sample.page_path))} tabindex="-1">{title}{mark}</a>'
    )


def cloud(
    samples: Sequence[Sample],
    page_rel: str,
    current: Sample | None = None,
    linked: bool = True,
) -> Markup:
    """Every instance as a dot, optionally marking one and linking them all.

    An instance page draws the cloud only to place itself in it, so its dots
    are bare: a link and a label on each of three hundred of them would be
    eight times the weight of the page carrying it.
    """

    ordered = [s for s in samples if s is not current]
    if current is not None:
        ordered.append(current)  # last, so the mark is not buried under the cloud
    dots = [_dot(sample, page_rel, sample is current, linked) for sample in ordered]
    # A cloud nobody can click is there to locate one instance, not to divide
    # the collection again: the stylesheet greys the rest of it out.
    kind = "cloud" if linked else "cloud locator"
    # the locator greys every dot but one, so a key to the two colours there
    # would explain a distinction the drawing is no longer making
    key = _legend(samples) if linked else []
    return Markup(
        f'<svg class="{kind}" viewBox="0 0 {_n(WIDTH)} {_n(HEIGHT)}"'
        ' xmlns="http://www.w3.org/2000/svg">'
        + "".join(_frame())
        + "".join(dots)
        + "".join(key)
        + "</svg>"
    )


# ---------------------------------------------------------------- provenance
#
# Both drawings sit beside prose that states the same facts, so they carry no
# label a reader would miss. What they add is shape: which side of a split this
# file is, and how little was taken out of a model to unbound it.

PROV_WIDTH = 620.0
_SPINE_X = 200.0
_FORK_DX = 110.0
_BRANCH_HEIGHT = 300.0


def taken_side(sense: str, value: int) -> tuple[str, int]:
    """The branch the search explored, given the one published here.

    A branch splits an integer variable, so the other side is the adjacent
    integer, not the same one: the file holding x >= 29 is the sibling of the
    node the search took at x <= 28.
    """

    return ("<=", value - 1) if sense == ">=" else (">=", value + 1)


def branch_diagram(sample: Sample) -> Markup:
    """The split behind a primal-infeasible file: what the search took, and this.

    The rungs between the root and the node are not drawn. path_head records
    the node's whole bound box, not the branches taken to reach it, so a ladder
    of twelve steps would claim an order nothing in the sidecar recorded.
    """

    branch = sample.primal
    published = int(branch.branch_value)
    taken, taken_int = taken_side(branch.branch_sense, published)
    left, right = _SPINE_X - _FORK_DX, _SPINE_X + _FORK_DX
    parts = [
        f'<svg class="prov" viewBox="0 0 {_n(PROV_WIDTH)} {_n(_BRANCH_HEIGHT)}"'
        ' xmlns="http://www.w3.org/2000/svg">',
        f'<line class="spine" x1="{_n(_SPINE_X)}" y1="30" x2="{_n(_SPINE_X)}" y2="170"/>',
        f'<circle class="node" cx="{_n(_SPINE_X)}" cy="30" r="7"/>',
        f'<text class="dim" x="{_n(_SPINE_X + 24)}" y="36">root</text>',
    ]
    if branch.depth > 1:
        parts.append(
            f'<text class="dim" x="{_n(_SPINE_X + 24)}" y="106">'
            f"{fmt_int(branch.depth - 1)} branchings</text>"
        )
    parts += [
        f'<circle class="node" cx="{_n(_SPINE_X)}" cy="170" r="7"/>',
        f'<text class="dim" x="{_n(_SPINE_X + 24)}" y="176">'
        f"parent, depth {fmt_int(branch.depth - 1)}</text>",
        # the fork: the side the search explored, and the side published here
        f'<path class="fork" d="M{_n(_SPINE_X)} 170 V210 H{_n(left)} V236"/>',
        f'<path class="fork here" d="M{_n(_SPINE_X)} 170 V210 H{_n(right)} V236"/>',
        f'<circle class="node" cx="{_n(left)}" cy="236" r="7"/>',
        f'<circle class="node here" cx="{_n(right)}" cy="236" r="7"/>',
        f'<text class="lbl" x="{_n(left)}" y="268" text-anchor="middle">'
        f"{escape(branch.branch_label)} {escape(taken)} {fmt_int(taken_int)}</text>",
        f'<text class="lbl here" x="{_n(right)}" y="268" text-anchor="middle">'
        f"{escape(branch.branch_label)} {escape(branch.branch_sense)} {fmt_int(published)}</text>",
        f'<text class="dim" x="{_n(left)}" y="292" text-anchor="middle">'
        "the search went here</text>",
        f'<text class="dim here" x="{_n(right)}" y="292" text-anchor="middle">this file</text>',
        "</svg>",
    ]
    return Markup("".join(parts))


# The dual drawing is a state change, not a magnitude: a relaxation that was
# bounded, the elements taken out of it, and what this file is. How many were
# taken is a number, and a number is already what the panel beside it states.
_BOX_W, _BOX_H, _BOX_Y = 180.0, 64.0, 54.0
_DROPS_HEIGHT = 160.0


def _state(x: float, label: str, caption: str, here: bool) -> list[str]:
    classes = "state here" if here else "state"
    mark = "lbl here" if here else "lbl"
    return [
        f'<rect class="{classes}" x="{_n(x)}" y="{_n(_BOX_Y)}"'
        f' width="{_n(_BOX_W)}" height="{_n(_BOX_H)}" rx="8"/>',
        f'<text class="{mark}" x="{_n(x + _BOX_W / 2)}" y="{_n(_BOX_Y + 40)}"'
        f' text-anchor="middle">{escape(label)}</text>',
        f'<text class="dim" x="{_n(x + _BOX_W / 2)}" y="142" text-anchor="middle">'
        f"{escape(caption)}</text>",
    ]


def _removed(dropped: int, unit: str) -> str:
    return f"{fmt_int(dropped)} {unit}" if dropped == 1 else f"{fmt_int(dropped)} {unit}s"


def drops_diagram(sample: Sample) -> Markup:
    """How this file came about: a bounded relaxation, less a minimal set."""

    drops = sample.dual
    head = (
        f'<svg class="prov drops" viewBox="0 0 {_n(PROV_WIDTH)} {_n(_DROPS_HEIGHT)}"'
        ' xmlns="http://www.w3.org/2000/svg">'
    )
    if drops.natural_unbounded:
        middle = (PROV_WIDTH - _BOX_W) / 2
        return Markup(
            head + "".join(_state(middle, "unbounded", "nothing was removed", True)) + "</svg>"
        )

    right = PROV_WIDTH - _BOX_W
    mid = PROV_WIDTH / 2
    taken = [
        _removed(count, unit)
        for count, unit in ((drops.bounds_dropped, "bound"), (drops.rows_dropped, "constraint"))
        if count
    ]
    parts = [head, *_state(0, "bounded", "root relaxation", False)]
    for row, phrase in enumerate(taken):
        prefix = "remove " if row == 0 else "and "
        parts.append(
            f'<text class="dim" x="{_n(mid)}" y="{_n(44 + row * 24)}" text-anchor="middle">'
            f"{prefix}{escape(phrase)}</text>"
        )
    parts += [
        f'<path class="arrow" d="M{_n(_BOX_W + 16)} 86 H{_n(right - 30)}"/>',
        f'<path class="arrow head" d="M{_n(right - 40)} 78 L{_n(right - 16)} 86'
        f' L{_n(right - 40)} 94"/>',
        *_state(right, "unbounded", "this file", True),
        "</svg>",
    ]
    return Markup("".join(parts))
