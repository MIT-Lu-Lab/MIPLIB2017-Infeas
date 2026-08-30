"""How one published file came about, drawn beside the prose that states it.

Both drawings carry no label a reader would miss, because the panel they sit
in says the same in words. What they add is shape: which side of a split a
primal-infeasible file is, and that a dual-infeasible one is a model left
otherwise intact.
"""

from __future__ import annotations

from ..content import fmt_int
from ..domain import Sample
from .markup import el, svg

WIDTH = 620.0

# The branch drawing: a spine from the root down to the parent, then a fork.
# The rungs between are not drawn. path_head records the node's whole bound
# box, not the branches taken to reach it, so a ladder of twelve steps would
# claim an order nothing in the sidecar recorded.
SPINE_X, FORK_DX = 200.0, 110.0
ROOT_Y, PARENT_Y, ELBOW_Y, CHILD_Y = 30.0, 170.0, 210.0, 236.0
MIDDLE_Y, BRANCH_Y, ROLE_Y = 106.0, 268.0, 292.0
LABEL_DX, NODE_R = 24.0, 7.0
BRANCH_HEIGHT = 300.0

# The state drawing: what the relaxation was, what was taken out, what it is.
BOX_W, BOX_H, BOX_Y = 180.0, 64.0, 54.0
BOX_TEXT_Y, CAPTION_Y, ARROW_Y = BOX_Y + 40, 142.0, 86.0
TAKEN_Y, TAKEN_STEP = 44.0, 24.0
DROPS_HEIGHT = 160.0


def taken_side(sense: str, value: int) -> tuple[str, int]:
    """The branch the search explored, given the one published here.

    A branch splits an integer variable, so the other side is the adjacent
    integer, not the same one: the file holding x >= 29 is the sibling of the
    node the search took at x <= 28.
    """

    return ("<=", value - 1) if sense == ">=" else (">=", value + 1)


def _child(x: float, label: str, role: str, here: bool) -> str:
    """One side of the fork: the bound it carries, and whose side it is."""

    suffix = " here" if here else ""
    return (
        el(
            "path",
            class_=f"fork{suffix}",
            d=f"M{SPINE_X:.0f} {PARENT_Y:.0f} V{ELBOW_Y:.0f} H{x:.0f} V{CHILD_Y:.0f}",
        )
        + el("circle", class_=f"node{suffix}", cx=x, cy=CHILD_Y, r=NODE_R)
        + el("text", label, class_=f"lbl{suffix}", x=x, y=BRANCH_Y, text_anchor="middle")
        + el("text", role, class_=f"dim{suffix}", x=x, y=ROLE_Y, text_anchor="middle")
    )


def branch_diagram(sample: Sample) -> str:
    """The split behind a primal-infeasible file: what the search took, and this."""

    branch = sample.primal
    published = int(branch.branch_value)
    taken, taken_int = taken_side(branch.branch_sense, published)
    parent_depth = fmt_int(branch.depth - 1)
    parts = [
        el("line", class_="spine", x1=SPINE_X, y1=ROOT_Y, x2=SPINE_X, y2=PARENT_Y),
        el("circle", class_="node", cx=SPINE_X, cy=ROOT_Y, r=NODE_R),
        el("text", "root", class_="dim", x=SPINE_X + LABEL_DX, y=ROOT_Y + 6),
    ]
    if branch.depth > 1:
        parts.append(
            el(
                "text",
                f"{parent_depth} branchings",
                class_="dim",
                x=SPINE_X + LABEL_DX,
                y=MIDDLE_Y,
            )
        )
    parts += [
        el("circle", class_="node", cx=SPINE_X, cy=PARENT_Y, r=NODE_R),
        el(
            "text",
            f"parent, depth {parent_depth}",
            class_="dim",
            x=SPINE_X + LABEL_DX,
            y=PARENT_Y + 6,
        ),
        _child(
            SPINE_X - FORK_DX,
            f"{branch.branch_label} {taken} {fmt_int(taken_int)}",
            "the search went here",
            here=False,
        ),
        _child(
            SPINE_X + FORK_DX,
            f"{branch.branch_label} {branch.branch_sense} {fmt_int(published)}",
            "this file",
            here=True,
        ),
    ]
    return svg("".join(parts), WIDTH, BRANCH_HEIGHT, class_="prov")


def _state(x: float, label: str, caption: str, here: bool) -> str:
    """A relaxation before or after: a box, what it is, and which one it is."""

    suffix = " here" if here else ""
    middle = x + BOX_W / 2
    return (
        el("rect", class_=f"state{suffix}", x=x, y=BOX_Y, width=BOX_W, height=BOX_H, rx=8)
        + el("text", label, class_=f"lbl{suffix}", x=middle, y=BOX_TEXT_Y, text_anchor="middle")
        + el("text", caption, class_="dim", x=middle, y=CAPTION_Y, text_anchor="middle")
    )


def _plural(count: int, unit: str) -> str:
    return f"{fmt_int(count)} {unit}" if count == 1 else f"{fmt_int(count)} {unit}s"


def drops_diagram(sample: Sample) -> str:
    """How this file came about: a bounded relaxation, less a minimal set."""

    drops = sample.dual
    if drops.natural_unbounded:
        middle = (WIDTH - BOX_W) / 2
        return svg(
            _state(middle, "unbounded", "nothing was removed", here=True),
            WIDTH,
            DROPS_HEIGHT,
            class_="prov drops",
        )

    right = WIDTH - BOX_W
    taken = [
        _plural(count, unit)
        for count, unit in ((drops.bounds_dropped, "bound"), (drops.rows_dropped, "constraint"))
        if count
    ]
    parts = [_state(0, "bounded", "root relaxation", here=False)]
    for row, phrase in enumerate(taken):
        parts.append(
            el(
                "text",
                f"{'remove ' if row == 0 else 'and '}{phrase}",
                class_="dim",
                x=WIDTH / 2,
                y=TAKEN_Y + row * TAKEN_STEP,
                text_anchor="middle",
            )
        )
    parts += [
        el("path", class_="arrow", d=f"M{BOX_W + 16:.0f} {ARROW_Y:.0f} H{right - 30:.0f}"),
        el(
            "path",
            class_="arrow head",
            d=f"M{right - 40:.0f} {ARROW_Y - 8:.0f} L{right - 16:.0f} {ARROW_Y:.0f} "
            f"L{right - 40:.0f} {ARROW_Y + 8:.0f}",
        ),
        _state(right, "unbounded", "this file", here=True),
    ]
    return svg("".join(parts), WIDTH, DROPS_HEIGHT, class_="prov drops")
