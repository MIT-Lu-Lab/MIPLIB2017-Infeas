"""The drawings a page carries, built from the index it already has.

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
`| safe` and cannot forget one. What goes inside is escaped by markup.el and
markup.group, which are the only two places that write an angle bracket.
"""

from __future__ import annotations

from collections.abc import Sequence

from markupsafe import Markup

from ..domain import Sample
from . import cloud as _cloud
from . import provenance as _provenance
from .cloud import (
    LIMITS,
    PAD_BOTTOM,
    PAD_LEFT,
    PAD_RIGHT,
    PAD_TOP,
    PLOT,
    R_MIN,
    position,
    radius,
)
from .markup import num
from .provenance import taken_side

__all__ = [
    "LIMITS",
    "PAD_BOTTOM",
    "PAD_LEFT",
    "PAD_RIGHT",
    "PAD_TOP",
    "PLOT",
    "R_MIN",
    "branch_diagram",
    "cloud",
    "drops_diagram",
    "num",
    "position",
    "radius",
    "taken_side",
]


def cloud(
    samples: Sequence[Sample],
    page_rel: str,
    current: Sample | None = None,
    linked: bool = True,
) -> Markup:
    """Every instance as a dot, optionally marking one and linking them all."""

    return Markup(_cloud.cloud(samples, page_rel, current, linked))


def branch_diagram(sample: Sample) -> Markup:
    """The split behind a primal-infeasible file."""

    return Markup(_provenance.branch_diagram(sample))


def drops_diagram(sample: Sample) -> Markup:
    """What was removed from a relaxation to leave its objective unbounded."""

    return Markup(_provenance.drops_diagram(sample))
