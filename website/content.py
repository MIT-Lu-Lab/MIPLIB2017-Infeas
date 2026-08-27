"""What the site says about the collection, in one place.

The same fact was written six times in four modules: the browse blurb, the
overview card, the overview masthead, the machine-readable description, the
about page and the guide each described a primal instance in their own words.
Correcting that description once meant finding all six, and the last time it was
corrected three were touched and the wording still drifted.

The registers differ on purpose. A card has room for two sentences and a meta
description has 160 characters, so they cannot be one string. They can be one
file: a change of position is edited here, and the neighbours that must agree
with it are on the screen.
"""

from __future__ import annotations

from .records import fmt_int

__all__ = ["ABOUT_DESCRIPTION", "DOWNLOAD_DESCRIPTION", "GUIDE_DESCRIPTION",
           "MASTHEAD_SUMMARY", "META_LIMIT", "NAME", "OVERVIEW_DESCRIPTION",
           "SUBSET_CARD", "SUBSET_META_SUMMARY", "SUBSET_SUMMARY", "TAGLINE",
           "collection_summary",
           "instance_description", "overview_description", "subset_description"]

# A search result shows about this much and then stops. A description written
# past it is a description whose end no reader sees, so a test holds every page
# to it rather than leaving it to whoever writes the next one.
META_LIMIT = 160

NAME = "MIPLIB-Infeas"
TAGLINE = "A benchmark of primal- and dual-infeasible linear programs"

# One sentence each, the shortest true statement of what a subset holds. The
# browse page shows this and the meta description quotes it.
SUBSET_SUMMARY = {
    "primal": "Linear programs with no feasible point. Each is the side of a branch "
              "that a branch-and-bound search did not explore, on a distinct MIPLIB "
              "2017 instance.",
    "dual": "Linear programs whose objective is unbounded, from MIPLIB 2017 root "
            "relaxations with a minimal set of bounds and constraints removed.",
}

# Under META_LIMIT with the count in front, for a search result. The page-visible
# summary above says the same thing at reading length and does not fit.
SUBSET_META_SUMMARY = {
    "primal": "linear programs with no feasible point, each the side of a branch a "
              "branch-and-bound search did not explore.",
    "dual": "linear programs with an unbounded objective, from MIPLIB 2017 root "
            "relaxations with a minimal set of bounds and rows removed.",
}

# The same fact with room to say how, for the overview cards.
SUBSET_CARD = {
    "primal": "A branch-and-bound run splits on a variable and explores one side of "
              "the split. This set collects the other side, at nodes where that side "
              "has no feasible point.",
    "dual": "Bounds and constraints are removed from a MIPLIB relaxation until the "
            "objective becomes unbounded, then every removal that proves unnecessary "
            "is restored.",
}

OVERVIEW_DESCRIPTION = ("{n} linear programs with no optimal solution, derived from "
                        "MIPLIB 2017 instances: {primal} primal-infeasible and {dual} "
                        "dual-infeasible.")

GUIDE_DESCRIPTION = ("Every field of the .meta.json sidecar beside a published "
                     "instance, and what each one does and does not claim.")
DOWNLOAD_DESCRIPTION = ("The archives and the per-subset indexes, and where a single "
                        "instance comes from.")
ABOUT_DESCRIPTION = ("How the instances were produced, which solver did what, and the "
                     "licence they carry.")


# The masthead says the same thing at reading length, and carries a link, so it
# is a template rather than a string. It lives here so that a correction to the
# summary above is made with this one on the screen.
MASTHEAD_SUMMARY = ("{n_samples} linear programs with no optimal solution, each "
                    "derived from a {miplib} instance with its integrality dropped. "
                    "{n_primal} have no feasible point and the other {n_dual} are "
                    "unbounded. They run up to {max_vars} variables and {max_cons} "
                    "constraints.")


def collection_summary(totals: dict) -> str:
    """What the collection is, at the length a dataset catalogue reads."""
    n = totals["counts"]
    return (f"{fmt_int(totals['n_samples'])} linear programs with no optimal solution, "
            "each derived from a MIPLIB 2017 instance with its integrality dropped. "
            f"{fmt_int(n.get('primal', 0))} have no feasible point, each the side of a "
            "branch a branch-and-bound search did not explore. The other "
            f"{fmt_int(n.get('dual', 0))} are feasible with an unbounded objective, "
            "produced by removing a minimal set of bounds and constraints from a root "
            f"relaxation. They run up to {fmt_int(totals['max_vars'])} variables and "
            f"{fmt_int(totals['max_cons'])} constraints.")


def overview_description(totals: dict) -> str:
    """The meta description of the site root."""
    n = totals["counts"]
    return OVERVIEW_DESCRIPTION.format(n=fmt_int(totals["n_samples"]),
                                       primal=fmt_int(n.get("primal", 0)),
                                       dual=fmt_int(n.get("dual", 0)))


def subset_description(subset: str, count: int) -> str:
    """The meta description of a browse page."""
    return f"{fmt_int(count)} {SUBSET_META_SUMMARY[subset]}"


def instance_description(instance: str, label: str, n_vars: int, n_cons: int) -> str:
    """The meta description of one instance page.

    Named first: a search result and a shared link both lead with the instance,
    and the reader is looking for that name rather than for the collection.
    """
    return (f"{instance}: a {label.lower()} linear program with "
            f"{fmt_int(n_vars)} variables and {fmt_int(n_cons)} constraints, "
            "from MIPLIB 2017.")
