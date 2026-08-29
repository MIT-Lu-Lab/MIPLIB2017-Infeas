"""What a page says, where a template cannot say it for itself.

Markup lives in render/templates. Here are the sentences that have to count
something before they can be written, the descriptions a page declares to a
search engine rather than shows, the names this collection is published
under, the software that produced the files, and two editorial rules: which
MIPLIB tags mean nothing once integrality is dropped, and how long a
description may run.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import CollectionTotals, Subset

NON_LP_TAGS = frozenset(
    {
        "binary",
        "mixed_binary",
        "integer_knapsack",
        "benchmark",
        "benchmark_suitable",
        "feasibility",
    }
)


def fmt_int(n: int) -> str:
    """Format a count with thousands separators."""

    return f"{n:,}"


def fmt_bytes(n: int) -> str:
    """Format a byte count with binary units."""

    if n < 1024:
        return f"{n} B"
    mb = n / (1024 * 1024)
    if mb < 0.1:
        return f"{n / 1024:.0f} KiB"
    if mb < 100:
        return f"{mb:.2f} MiB"
    if mb < 1024:
        return f"{mb:.1f} MiB"
    return f"{mb / 1024:.2f} GiB"


# A search result shows about this much and then stops. A description written
# past it is a description whose end no reader sees, so a test holds every page
# to it rather than leaving it to whoever writes the next one.
META_LIMIT = 160

NAME = "MIPLIB2017-Infeas"
PUBLIC_SITE_URL = "https://mit-lu-lab.github.io/MIPLIB2017-Infeas/"
SIDECAR_SCHEMA_PATH = "schema/sidecar/1.0.1/meta.schema.json"
TAGLINE = "A benchmark of primal- and dual-infeasible linear programs"


@dataclass(frozen=True)
class Software:
    """One program that produced the published files, and what it did."""

    name: str
    version: str
    role: str


# Naming a solver without its version describes a run nobody can repeat: which
# nodes a branch-and-bound tree holds depends on the solver that built it, and
# what a presolve run disposes of changes between releases. The about page
# renders these and a test holds the README to the same versions, so the two
# cannot come apart.
SOFTWARE = (
    Software(
        "CPLEX",
        "22.1.2.1",
        "Built the branch-and-bound trees the primal-infeasible set is taken from, and "
        "ran the loop that drops bounds and constraints for the dual-infeasible one.",
    ),
    Software(
        "HiGHS",
        "1.14.0",
        "The first presolver a candidate had to survive, reached through the highspy bindings.",
    ),
    Software(
        "Gurobi",
        "12.0.3",
        "The second presolver a candidate had to survive.",
    ),
    Software(
        "Python",
        "3.11.9",
        "Ran the mining code driving all three: the callback that follows the search, "
        "the drop loop, and the selection.",
    ),
)

# One sentence each, the shortest true statement of what a subset holds. The
# browse page shows this and the meta description quotes it.
SUBSET_SUMMARY = {
    "primal": "Linear programs with no feasible point. Each is the side of a branch "
    "that a branch-and-bound search did not explore, on a distinct MIPLIB "
    "2017 instance.",
    # a definition with no counts in it; how the set divides is dual_derivation(),
    # which depends on how many relaxations were already unbounded
    "dual": "Linear programs whose objective is unbounded.",
}

# Under META_LIMIT with the count in front, for a search result. The page-visible
# summary above says the same thing at reading length and does not fit.
SUBSET_META_SUMMARY = {
    "primal": "linear programs with no feasible point, each from the unexplored side "
    "of a branch in a branch-and-bound search.",
    "dual": "linear programs with an unbounded objective, derived from MIPLIB 2017 "
    "root relaxations.",
}

# The same fact with room to say how, for the overview cards.
SUBSET_CARD = {
    "primal": "A branch-and-bound run splits on a variable and explores one side of "
    "the split. This set collects the other side, at nodes where that side "
    "has no feasible point.",
    # the dual half is dual_derivation(), as above
}

OVERVIEW_DESCRIPTION = (
    "{n} linear programs with no optimal solution, derived from "
    "MIPLIB 2017 instances: {primal} primal-infeasible and {dual} "
    "dual-infeasible."
)

GUIDE_DESCRIPTION = (
    "Every field of the .meta.json sidecar beside a published "
    "instance, and what each one does and does not claim."
)
DOWNLOAD_DESCRIPTION = (
    "The archives and the per-subset indexes, and where a single instance comes from."
)
ABOUT_DESCRIPTION = (
    "How the instances were produced, which solver did what, and the terms each one carries."
)


def dual_derivation(dual: int, natural: int) -> str:
    """Describe the dual subset's derivation paths from supplied counts."""
    if not dual:
        return ""
    removed = (
        "removing an inclusion-minimal set of bounds and constraints from a "
        "feasible, bounded root relaxation"
    )
    constructed = dual - natural
    if not natural:
        each = "The one comes" if dual == 1 else "Each comes"
        return f"{each} from {removed}."
    if not constructed:
        each = "The one was" if dual == 1 else "Each was"
        return f"{each} already unbounded, with nothing removed."
    # a lone one reads as a word: "the other 1 was" is a line of a table, not a
    # sentence
    made = "one comes" if constructed == 1 else f"{fmt_int(constructed)} come"
    rest = "the other was" if natural == 1 else f"the other {fmt_int(natural)} were"
    return f"Of those, {made} from {removed}; {rest} already unbounded."


def collection_summary(totals: CollectionTotals) -> str:
    """What the collection is, at the length a dataset catalogue reads."""
    n = totals["counts"]
    primal = n["primal"]
    dual = n["dual"]
    natural = totals["natural_unbounded"]
    primal_verb = "has" if primal == 1 else "have"
    return (
        f"{fmt_int(totals['n_samples'])} linear programs with no optimal solution, "
        "each derived from a MIPLIB 2017 instance with its integrality dropped. "
        f"{fmt_int(primal)} {primal_verb} no feasible point, each from the "
        "unexplored side of a branch in a branch-and-bound search, and "
        f"{fmt_int(dual)} have an unbounded objective. "
        f"{dual_derivation(dual, natural)} They run up to "
        f"{fmt_int(totals['max_vars'])} variables and "
        f"{fmt_int(totals['max_cons'])} constraints."
    )


def overview_description(totals: CollectionTotals) -> str:
    """The meta description of the site root."""
    n = totals["counts"]
    return OVERVIEW_DESCRIPTION.format(
        n=fmt_int(totals["n_samples"]),
        primal=fmt_int(n["primal"]),
        dual=fmt_int(n["dual"]),
    )


def subset_summary(subset: Subset, count: int, natural_unbounded: int = 0) -> str:
    """What a browse page shows under its heading.

    The primal name says what the set holds; the dual one does not, so that
    half is defined before it is divided.
    """
    if subset != "dual":
        return SUBSET_SUMMARY[subset]
    return f"{SUBSET_SUMMARY['dual']} {dual_derivation(count, natural_unbounded)}"


def subset_card(subset: Subset, count: int, natural_unbounded: int = 0) -> str:
    """The blurb on an overview card."""
    if subset != "dual":
        return SUBSET_CARD[subset]
    return dual_derivation(count, natural_unbounded)


def imported_sources_note(imported: int) -> str:
    """Describe imported sources without hard-coding their count."""
    if imported == 1:
        return "the one source imported from an earlier MIPLIB, which carries"
    return f"the {fmt_int(imported)} sources imported from an earlier MIPLIB, which carry"


def subset_description(subset: Subset, count: int, natural_unbounded: int = 0) -> str:
    """The meta description of a browse page."""
    if subset == "dual" and natural_unbounded:
        constructed = count - natural_unbounded
        return (
            f"{fmt_int(count)} linear programs with an unbounded objective: "
            f"{fmt_int(constructed)} use an inclusion-minimal relaxation; "
            f"{fmt_int(natural_unbounded)} were unbounded as given."
        )
    return f"{fmt_int(count)} {SUBSET_META_SUMMARY[subset]}"


def instance_description(instance: str, label: str, n_vars: int, n_cons: int) -> str:
    """The meta description of one instance page, led by its name."""
    return (
        f"{instance}: a {label.lower()} linear program with "
        f"{fmt_int(n_vars)} variables and {fmt_int(n_cons)} constraints, "
        "from MIPLIB 2017."
    )
