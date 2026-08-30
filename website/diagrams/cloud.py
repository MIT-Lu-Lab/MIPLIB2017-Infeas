"""The collection as one dot per instance, on logarithmic axes.

The overview shows it whole, with every dot a link to the instance it stands
for. An instance page shows the same picture to place itself in it, with the
rest greyed out by the stylesheet and no links at all: three hundred labelled
anchors would weigh several times the page carrying them.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..content import fmt_int
from ..domain import Sample
from ..urls import rel
from .markup import el, group, num, power_of_ten, svg

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
RIGHT, BOTTOM = PAD_LEFT + PLOT, PAD_TOP + PLOT

# Decade gridlines, the ones that fall inside LIMITS.
DECADES = tuple(10**e for e in range(2, 8))
TICK_DROP, TICK_INSET = 46.0, 20.0

# A dot's radius over the collection's nonzero range. A published instance has
# at least 10^5 nonzeros and the largest has under 10^8, so the span is under
# three decades. What catches the pointer is a fat transparent stroke set in
# the stylesheet, which costs no markup at all.
NZ_REF, R_BASE, R_PER_DECADE, R_MIN = 5.0, 7.0, 3.2, 3.0

# The key sits inside the frame: identity at the top left, where the cloud is
# thin, and the size scale at the bottom right, where nothing lands because an
# instance with few constraints and many variables is not a shape MIPLIB holds.
KEY_X, KEY_Y, KEY_STEP = 168.0, 76.0, 46.0
SIZE_X, SIZE_Y, SIZE_STEP = 1046.0, 852.0, 62.0

TONES = (("primal", "p", "Infeasible"), ("dual", "d", "Unbounded"))


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
    y = BOTTOM - (math.log10(n_cons) - lo) / span * PLOT
    return _clamp(x, PAD_LEFT, RIGHT), _clamp(y, PAD_TOP, BOTTOM)


def radius(nnz: int) -> float:
    """A dot's radius, growing with the decade of its nonzero count."""

    return max(R_MIN, R_BASE + R_PER_DECADE * (math.log10(nnz) - NZ_REF))


def _frame() -> str:
    """The box, its decade grid and the axis labels, under everything else."""

    parts = [el("rect", class_="frame", x=PAD_LEFT, y=PAD_TOP, width=PLOT, height=PLOT)]
    for decade in DECADES:
        x, y = position(decade, decade)
        exponent = int(math.log10(decade))
        parts += [
            el("line", class_="grid", x1=x, y1=PAD_TOP, x2=x, y2=BOTTOM),
            el("line", class_="grid", x1=PAD_LEFT, y1=y, x2=RIGHT, y2=y),
            group("text", power_of_ten(exponent), class_="tick x", x=x, y=BOTTOM + TICK_DROP),
            group(
                "text",
                power_of_ten(exponent),
                class_="tick y",
                x=PAD_LEFT - TICK_INSET,
                y=y + 12,
            ),
        ]
    parts += [
        el("text", "# variables", class_="axis-label x", x=PAD_LEFT + PLOT / 2, y=HEIGHT - 8),
        el(
            "text",
            "# constraints",
            class_="axis-label y",
            x=-(PAD_TOP + PLOT / 2),
            y=30,
            transform="rotate(-90)",
        ),
    ]
    return "".join(parts)


def _legend(samples: Sequence[Sample]) -> str:
    """Which colour is which half, and what a dot's size means."""

    counts = {subset: sum(1 for s in samples if s.subset == subset) for subset, _, _ in TONES}
    parts = []
    for row, (subset, tone, label) in enumerate(TONES):
        y = KEY_Y + row * KEY_STEP
        # grouped, so the filter that hides one half hides its key with it
        parts.append(
            group(
                "g",
                el("circle", class_=tone, cx=KEY_X, cy=y, r=9)
                + el(
                    "text",
                    f"{label} ({fmt_int(counts[subset])})",
                    class_="key",
                    x=KEY_X + 24,
                    y=y + 10,
                ),
                class_=f"key-{tone}",
            )
        )
    parts.append(
        el("text", "nonzeros", class_="key dim", x=SIZE_X, y=SIZE_Y - 34, text_anchor="end")
    )
    for row, exponent in enumerate((5, 6, 7)):
        y = SIZE_Y + row * SIZE_STEP
        parts += [
            el("circle", class_="key-dot", cx=SIZE_X, cy=y, r=radius(10**exponent)),
            group(
                "text",
                power_of_ten(exponent, dy=-11),
                class_="key dim",
                x=SIZE_X - 26,
                y=y + 9,
                text_anchor="end",
            ),
        ]
    return "".join(parts)


def _dot(sample: Sample, page_rel: str, here: bool, linked: bool) -> str:
    x, y = position(sample.n_vars, sample.n_cons)
    tone = "p" if sample.subset == "primal" else "d"
    mark = el(
        "circle",
        class_=f"{tone} here" if here else tone,
        cx=x,
        cy=y,
        r=radius(sample.nnz),
    )
    if not linked and not here:
        return mark
    title = el(
        "title",
        f"{sample.instance}: {fmt_int(sample.n_vars)} \N{MULTIPLICATION SIGN} "
        f"{fmt_int(sample.n_cons)}, {fmt_int(sample.nnz)} nonzeros",
    )
    if not linked:
        return group("g", title + mark)
    # tabindex=-1: every dot repeats a row of a browse page, which is
    # searchable, sortable and already reachable by keyboard.
    return group("a", title + mark, href=rel(page_rel, sample.page_path), tabindex=-1)


def cloud(
    samples: Sequence[Sample],
    page_rel: str,
    current: Sample | None = None,
    linked: bool = True,
) -> str:
    """Every instance as a dot, optionally marking one and linking them all."""

    ordered = [s for s in samples if s is not current]
    if current is not None:
        ordered.append(current)  # last, so the mark is not buried under the cloud
    dots = "".join(_dot(sample, page_rel, sample is current, linked) for sample in ordered)
    # A cloud nobody can click locates one instance rather than dividing the
    # collection again, so the stylesheet greys the rest of it out and the key
    # to the two colours would explain a distinction it is no longer making.
    return svg(
        _frame() + dots + (_legend(samples) if linked else ""),
        WIDTH,
        HEIGHT,
        class_="cloud" if linked else "cloud locator",
    )


__all__ = [
    "LIMITS",
    "PAD_BOTTOM",
    "PAD_LEFT",
    "PAD_RIGHT",
    "PAD_TOP",
    "PLOT",
    "R_MIN",
    "cloud",
    "num",
    "position",
    "radius",
]
