"""Redraw the figure the overview page shows, from the index it is built from.

Variables against constraints, one mark per published instance, on logarithmic
axes with a shared range and a square panel, so a decade is the same distance
either way. Hue carries the class and the mark area carries the nonzero count.

Two files ship, one per medium. The site is dark, so the screen figure is drawn
on the site's own ground in the site's own class colours; the print figure is
the light one, for the same reason the stylesheet keeps a light palette for
print. The result is committed and the build copies it, so nothing at build
time depends on matplotlib.

    pip install --group figure
    python -m scripts.plot_size_scatter
    python -m scripts.plot_size_scatter --pdf .    # the paper's copy, vector

LaTeX is used for the labels when a TeX installation is on PATH, so the figure
sets in the same letterforms as the paper it also appears in; without one,
matplotlib's bundled Computer Modern stands in and looks the same.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401  (registers the styles)
from matplotlib.lines import Line2D

from website import FIGURE_DIR, INDEX_FILE
from website.content import FIGURE_PRINT, FIGURE_SCREEN

# Print is Paul Tol's vibrant scheme, used as given (protan dE 22.7, normal
# 33.4); its one warning is the orange at 2.79:1 against white, which the
# legend relieves.
#
# Screen is not a second choice of colour: it is --primal and --dual from the
# site's own stylesheet, because the figure sits on pages already colour-coded
# by those two. They separate well (protan dE 22.8) and clear the surface
# contrast, but sit above the dark lightness band; the site's identity wins
# that trade.
THEMES = {
    "screen": {
        "name": Path(FIGURE_SCREEN).name,
        "primal": "#8B99EC",
        "dual": "#E0A458",
        "surface": "#0F1116",
        "ink": "#E6E8EF",
        "rule": "#272B37",
        "axis": "#3A4050",
        "key": "#959BAC",
        # Alpha darkens a mark towards a dark ground, so the fill is carried
        # higher here than on white to keep an isolated instance legible.
        "fill_alpha": 0.62,
        "ring": 0.0,
    },
    "print": {
        "name": Path(FIGURE_PRINT).name,
        "primal": "#0077BB",
        "dual": "#EE7733",
        "surface": "#FFFFFF",
        "ink": "#1A1A1A",
        "rule": "#E6E6E6",
        "axis": "#B0B0B0",
        "key": "#9E9E9E",
        "fill_alpha": 0.65,
        # A hairline of the surface colour around every disc. Without it two
        # overlapping translucent marks read as one patch of a third colour.
        "ring": 0.4,
    },
}

# One range for both axes, covering 27 constraints to 20.7M variables.
LIMITS = (1.8e1, 4.0e7)

# Mark area in points^2, linear in log10(nonzeros).
NZ_REF = 5.0
AREA_BASE, AREA_SLOPE = 5.0, 24.0

# Searched in order when latex is not already on PATH.
TEX_BIN_CANDIDATES = (
    r"D:\Programs\MiKTeX\miktex\bin\x64",
    r"C:\Program Files\MiKTeX\miktex\bin\x64",
)


def area(nnz: int) -> float:
    """Mark area for one instance, so a decade of nonzeros is a fixed step."""

    return AREA_BASE + AREA_SLOPE * (math.log10(nnz) - NZ_REF)


def load(index_path: Path) -> dict[str, tuple[list[int], list[int], list[float]]]:
    """Read the site index into per-subset columns of x, y, and mark area."""

    records = json.loads(index_path.read_text(encoding="utf-8"))["records"]
    return {
        subset: (
            [r["n_vars"] for r in records if r["subset"] == subset],
            [r["n_cons"] for r in records if r["subset"] == subset],
            [area(r["nnz"]) for r in records if r["subset"] == subset],
        )
        for subset in ("primal", "dual")
    }


def find_tex(explicit: str | None) -> bool:
    """Put a LaTeX installation on PATH, and report whether one is usable."""

    for candidate in ([explicit] if explicit else []) + list(TEX_BIN_CANDIDATES):
        if candidate and Path(candidate, "latex.exe").exists():
            os.environ["PATH"] = candidate + os.pathsep + os.environ["PATH"]
            break
    return bool(shutil.which("latex") and shutil.which("dvipng"))


def draw(theme: str, data, usetex: bool, counts: dict[str, int]):
    """Draw one theme's figure and return it."""

    t = THEMES[theme]
    plt.style.use(["science", "grid"] + ([] if usetex else ["no-latex"]))
    plt.rcParams.update(
        {
            "font.size": 8.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 8,
            "grid.color": t["rule"],
            "grid.linewidth": 0.35,
            "grid.linestyle": "-",
            "figure.facecolor": t["surface"],
            "axes.facecolor": t["surface"],
            "axes.edgecolor": t["axis"],
            "axes.linewidth": 0.5,
            "xtick.color": t["axis"],
            "ytick.color": t["axis"],
            "xtick.labelcolor": t["ink"],
            "ytick.labelcolor": t["ink"],
            "text.color": t["ink"],
        }
    )
    if not usetex:
        plt.rcParams.update(
            {
                "font.family": "serif",
                "font.serif": ["cmr10", "DejaVu Serif"],
                "mathtext.fontset": "cm",
                "axes.formatter.use_mathtext": True,
                "axes.unicode_minus": False,
            }
        )

    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*LIMITS)
    ax.set_ylim(*LIMITS)
    ax.set_box_aspect(1)
    ax.set_axisbelow(True)

    # The smaller class goes on top, so it is not buried by the larger one.
    for subset, z in (("primal", 2), ("dual", 3)):
        x, y, s = data[subset]
        ax.scatter(
            x,
            y,
            s=s,
            facecolors=t[subset],
            alpha=t["fill_alpha"],
            zorder=z,
            edgecolors=t["surface"] if t["ring"] else "none",
            linewidths=t["ring"],
        )

    # "#" is a parameter character to LaTeX, so it has to be escaped there.
    hash_ = r"\#" if usetex else "#"
    ax.set_xlabel(f"{hash_} variables", color=t["ink"])
    ax.set_ylabel(f"{hash_} constraints", color=t["ink"])

    identity = ax.legend(
        handles=[
            Line2D(
                [],
                [],
                color=t[subset],
                marker="o",
                linestyle="none",
                markersize=5.5,
                markeredgecolor="none",
                alpha=0.75,
                label=f"{label} ({counts[subset]})",
            )
            for subset, label in (("primal", "Infeasible"), ("dual", "Unbounded"))
        ],
        loc="upper left",
        frameon=False,
        labelcolor=t["ink"],
        handletextpad=0.5,
        borderaxespad=0.7,
        labelspacing=0.5,
    )
    ax.add_artist(identity)

    size_key = ax.legend(
        handles=[
            Line2D(
                [],
                [],
                color=t["key"],
                marker="o",
                linestyle="none",
                markersize=math.sqrt(area(10**e)),
                markeredgewidth=0,
                alpha=0.55,
                label=f"$10^{{{e}}}$",
            )
            for e in (5, 6, 7)
        ],
        loc="lower right",
        frameon=False,
        labelcolor=t["ink"],
        title=f"{hash_} nonzeros",
        title_fontsize=8,
        fontsize=8,
        handletextpad=0.8,
        labelspacing=1.05,
        borderaxespad=0.7,
    )
    size_key.get_title().set_color(t["ink"])
    fig.tight_layout(pad=0.3)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--index", type=Path, default=INDEX_FILE)
    parser.add_argument("--out-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument(
        "--pdf",
        type=Path,
        help="also write the print figure as a PDF into this directory",
    )
    parser.add_argument("--tex-bin", help="directory holding latex.exe and dvipng.exe")
    parser.add_argument(
        "--no-usetex",
        dest="usetex",
        action="store_false",
        help="skip LaTeX and use matplotlib's bundled Computer Modern",
    )
    args = parser.parse_args()

    usetex = args.usetex and find_tex(args.tex_bin)
    if args.usetex and not usetex:
        print("no LaTeX found; using matplotlib's Computer Modern")

    data = load(args.index)
    counts = {subset: len(columns[0]) for subset, columns in data.items()}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for theme, spec in THEMES.items():
        fig = draw(theme, data, usetex, counts)
        path = args.out_dir / spec["name"]
        fig.savefig(path, bbox_inches="tight", facecolor=spec["surface"])
        print(f"wrote {path}")
        if theme == "print" and args.pdf:
            pdf = args.pdf / Path(spec["name"]).with_suffix(".pdf").name
            fig.savefig(pdf, bbox_inches="tight", facecolor=spec["surface"])
            print(f"wrote {pdf}")
        plt.close(fig)


if __name__ == "__main__":
    main()
