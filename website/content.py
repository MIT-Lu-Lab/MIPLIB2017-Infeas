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
           "PUBLIC_SITE_URL", "SUBSET_CARD", "SUBSET_META_SUMMARY",
           "SUBSET_SUMMARY", "TAGLINE",
           "collection_summary",
           "instance_description", "overview_description", "subset_description"]

# A search result shows about this much and then stops. A description written
# past it is a description whose end no reader sees, so a test holds every page
# to it rather than leaving it to whoever writes the next one.
META_LIMIT = 160

NAME = "MIPLIB2017-Infeas"
PUBLIC_SITE_URL = "https://mit-lu-lab.github.io/MIPLIB2017-Infeas/"
TAGLINE = "A benchmark of primal- and dual-infeasible linear programs"

# One sentence each, the shortest true statement of what a subset holds. The
# browse page shows this and the meta description quotes it.
SUBSET_SUMMARY = {
    "primal": "Linear programs with no feasible point. Each is the side of a branch "
              "that a branch-and-bound search did not explore, on a distinct MIPLIB "
              "2017 instance.",
    "dual": "Linear programs whose objective is unbounded. For 103, an "
            "inclusion-minimal set of bounds and constraints was removed from a "
            "feasible, bounded MIPLIB 2017 root relaxation; two were unbounded as given.",
}

# Under META_LIMIT with the count in front, for a search result. The page-visible
# summary above says the same thing at reading length and does not fit.
SUBSET_META_SUMMARY = {
    "primal": "linear programs with no feasible point, each the side of a branch a "
              "branch-and-bound search did not explore.",
    "dual": "linear programs with an unbounded objective, derived from MIPLIB 2017 "
            "root relaxations.",
}

# The same fact with room to say how, for the overview cards.
SUBSET_CARD = {
    "primal": "A branch-and-bound run splits on a variable and explores one side of "
              "the split. This set collects the other side, at nodes where that side "
              "has no feasible point.",
    "dual": "Of the 105 root LP relaxations, 103 become unbounded after an "
            "inclusion-minimal set of bounds and constraints is removed; two are "
            "unbounded as given.",
}

OVERVIEW_DESCRIPTION = ("{n} linear programs with no optimal solution, derived from "
                        "MIPLIB 2017 instances: {primal} primal-infeasible and {dual} "
                        "dual-infeasible.")

GUIDE_DESCRIPTION = ("Every field of the .meta.json sidecar beside a published "
                     "instance, and what each one does and does not claim.")
DOWNLOAD_DESCRIPTION = ("The archives and the per-subset indexes, and where a single "
                        "instance comes from.")
ABOUT_DESCRIPTION = ("How the instances were produced, which solver did what, and the "
                     "terms each one carries.")


# The masthead says the same thing at reading length, and carries a link, so it
# is a template rather than a string. It lives here so that a correction to the
# summary above is made with this one on the screen.
MASTHEAD_SUMMARY = ("{n_samples} linear programs with no optimal solution, each "
                    "derived from a {miplib} instance with its integrality dropped. "
                    "{n_primal} {primal_verb} no feasible point; {n_dual} {dual_verb} "
                    "unbounded. They run up to {max_vars} variables and {max_cons} "
                    "constraints.")


def _dual_derivation(totals: dict) -> str:
    """Describe both ways a dual-infeasible member enters the collection."""
    dual = totals["counts"].get("dual", 0)
    natural = totals.get("natural_unbounded", 0)
    constructed = dual - natural
    program = "program" if dual == 1 else "programs"
    was = "was" if dual == 1 else "were"
    if not dual:
        return ""
    if not natural:
        return (f"The {fmt_int(dual)} dual-infeasible {program} {was} made unbounded "
                "by removing an inclusion-minimal set of bounds and constraints from "
                "a feasible, bounded root relaxation.")
    if not constructed:
        return (f"The {fmt_int(dual)} dual-infeasible {program} {was} already "
                "unbounded as given.")
    relaxations = "relaxation was" if natural == 1 else "relaxations were"
    made = "was" if constructed == 1 else "were"
    return (f"Of the {fmt_int(dual)} dual-infeasible {program}, "
            f"{fmt_int(constructed)} {made} made unbounded by removing an "
            "inclusion-minimal set of bounds and constraints from a feasible, bounded "
            f"root relaxation; {fmt_int(natural)} root {relaxations} already unbounded.")


def collection_summary(totals: dict) -> str:
    """What the collection is, at the length a dataset catalogue reads."""
    n = totals["counts"]
    primal = n.get("primal", 0)
    primal_verb = "has" if primal == 1 else "have"
    return (f"{fmt_int(totals['n_samples'])} linear programs with no optimal solution, "
            "each derived from a MIPLIB 2017 instance with its integrality dropped. "
            f"{fmt_int(primal)} {primal_verb} no feasible point, each the side of a "
            "branch a branch-and-bound search did not explore. "
            f"{_dual_derivation(totals)} They run up to "
            f"{fmt_int(totals['max_vars'])} variables and "
            f"{fmt_int(totals['max_cons'])} constraints.")


def overview_description(totals: dict) -> str:
    """The meta description of the site root."""
    n = totals["counts"]
    return OVERVIEW_DESCRIPTION.format(n=fmt_int(totals["n_samples"]),
                                       primal=fmt_int(n.get("primal", 0)),
                                       dual=fmt_int(n.get("dual", 0)))


def subset_description(subset: str, count: int, natural_unbounded: int = 0) -> str:
    """The meta description of a browse page."""
    if subset == "dual" and natural_unbounded:
        constructed = count - natural_unbounded
        return (f"{fmt_int(count)} linear programs with an unbounded objective: "
                f"{fmt_int(constructed)} use an inclusion-minimal relaxation; "
                f"{fmt_int(natural_unbounded)} were unbounded as given.")
    return f"{fmt_int(count)} {SUBSET_META_SUMMARY[subset]}"


def instance_description(instance: str, label: str, n_vars: int, n_cons: int) -> str:
    """The meta description of one instance page.

    Named first: a search result and a shared link both lead with the instance,
    and the reader is looking for that name rather than for the collection.
    """
    return (f"{instance}: a {label.lower()} linear program with "
            f"{fmt_int(n_vars)} variables and {fmt_int(n_cons)} constraints, "
            "from MIPLIB 2017.")
