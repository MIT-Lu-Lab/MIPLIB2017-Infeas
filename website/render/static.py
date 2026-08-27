"""Pages that do not vary with an instance: guide, download, about."""

from __future__ import annotations

from ..records import SUBSET_META, fmt_bytes, fmt_int
from .shell import Markup, el, fmt, join, page

CARD = """<div class="card {tone}">
  <header><span class="eyebrow">{label}</span></header>
  <div class="body">
    {zip_btn}
    <a class="btn ghost" href="../{slug}.csv">{slug}.csv<span class="sz">index</span></a>
    <p class="hint">The archive unpacks to <span class="mono">instances/{d}/</span>. The
    index lists every instance in this subset with its dimensions and the filename to
    fetch.</p>
  </div>
</div>"""

GUIDE = """
<div class="masthead">
  <span class="eyebrow">Reference</span>
  <h1>Reading a file</h1>
  <p class="sub">Every published instance is a gzipped MPS beside a
  <span class="mono">.meta.json</span> sidecar recording how it was derived. The reference
  below explains each field; the <a href="../schema/meta.schema.json">JSON Schema</a>
  is the machine-readable contract.</p>
</div>

<div class="section">
  <h2>Both subsets</h2>
  {common}
</div>

<div class="section">
  <h2>Primal-infeasible</h2>
  {primal}
</div>

<div class="section">
  <h2>Dual-infeasible</h2>
  {dual}
</div>

<div class="section">
  <h2>Fields you can ignore</h2>
  <div class="prose">
    <p class="muted">These are artefacts of the pipeline that produced the collection.
    They are kept so a file can be traced back to the run that made it, and are not
    properties of the linear program.</p>
  </div>
  {internal}
</div>
"""

DOWNLOAD = """
<div class="masthead">
  <span class="eyebrow">Files</span>
  <h1>Download</h1>
  <p class="sub">{n_samples} instances. The archives below carry both
  files of every instance{in_all}.</p>
</div>
<div class="pair">{cards}</div>
<p class="note">Single instances download from
their own page. Every asset sits directly under the release prefix, so a filename taken
from an index is all you need to append.</p>
"""

ABOUT = """
<div class="masthead">
  <span class="eyebrow">Background</span>
  <h1>About this collection</h1>
</div>
<div class="section">
  <h2>Primal-infeasible instances</h2>
  <div class="prose">
    <p>A CPLEX branch-and-bound run explores a MIPLIB 2017 instance with
    cuts, presolve, probing and primal heuristics switched off. A callback follows the
    search, infers the branch taken at each step from the one integral bound that changes
    on an integer variable, and re-solves the opposite side on a standalone LP template.
    When that side has no feasible point, it is written out. The bounds come from a
    branch the run actually took, not from bounds tightened at random.</p>
  </div>
</div>
<div class="section">
  <h2>Dual-infeasible instances</h2>
  <div class="prose">
    <p>Where the source instance's LP relaxation is feasible with a
    bounded optimum, bounds and constraints are removed one at a time, each drawn from the optimal
    dual support, until the objective becomes unbounded. A second pass then restores every
    removal that turns out not to be needed, so the published set is minimal: put any one
    element back and the LP is bounded again. Because relaxing a feasible problem cannot
    make it infeasible, every one of these is genuinely unbounded rather than empty.</p>
  </div>
</div>
<div class="section">
  <h2>What survives to publication</h2>
  <div class="prose">
    <p>A candidate is kept only if neither HiGHS nor Gurobi presolve settles
    it on its own. Anything either presolver disposes of unaided is discarded as trivial.
    One instance per source instance per subset is then selected, reproducibly, from the
    candidates that survived.</p>
  </div>
</div>
<div class="section">
  <h2>Which solver did what</h2>
  <div class="prose">
    <p>CPLEX produced the collection. It ran the branch-and-bound search
    behind the primal-infeasible set, and it solved every LP in the drop-and-restore loop
    behind the dual-infeasible set. Which nodes a tree contains depends on the solver that
    built it, so reproducing this collection means reproducing that run.</p>
    <p>HiGHS and Gurobi supply the presolve gates described above. Neither
    contributes an instance; they only reject the ones their presolve settles unaided.</p>
  </div>
</div>
<div class="section">
  <h2>Source and licence</h2>
  <div class="prose">
    <p>Every instance derives from the MIPLIB 2017 collection at
    <a href="https://miplib.zib.de/">miplib.zib.de</a>, which should be cited alongside
    this collection.</p>
    <p>MIPLIB 2017 requires every contributed instance to carry a licence
    granting redistribution, by default CC BY-SA 4.0. The instances here are adapted material
    under that licence: each keeps its source instance's constraint matrix, objective and
    right-hand side, and changes the variable bounds, the integrality, and in the dual set the
    rows.
    ShareAlike therefore carries over, and this collection is released under
    <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a> as well.</p>
  </div>
</div>
"""


# U+00A0: the operator and its number are one token to a reader and
# must not be split across a line break.
NBSP = chr(0xA0)

def mono(text: str) -> Markup:
    """Code voice for a field name or a literal."""
    return el("span", text, class_="mono")


def _dl(rows) -> Markup:
    """A field reference block: name, type, and what it means."""
    return el("dl", join(
        join((el("dt", el("span", name, class_="mono"),
                 el("span", kind, class_="ftype")),
              el("dd", body)))
        for name, kind, body in rows), class_="fields")


def render_guide() -> str:
    """Reference for every field in a sidecar and every figure on a page.

    Without this a reader cannot tell that `drops[].var` is a 0-based column
    index, or that a dropped row's coefficients are not recorded, so the
    minimality claim is not checkable from what is published.
    """
    common = _dl([
        ("instance", "string",
         fmt("Name of the MIPLIB 2017 instance this one derives from. The published "
             "file is that name plus {a} or {b}.", a=mono("_if"), b=mono("_ub"))),
        ("sample_kind", "string",
         fmt("Which half the file belongs to: {primal} for the primal set, {dual} for "
             "the dual one. The first name is older than the wording on these pages "
             "and claims more than the file records: what it holds is the side of a "
             "branch the search did not explore.",
             primal=mono("pruned_infeasible_sibling"),
             dual=mono("lp_unbounded_after_drop"))),
        ("n_vars, n_cons, nnz", "integer",
         fmt("Columns, rows and matrix nonzeros of the published file, counted from "
             "the file itself rather than from the model that produced it. The "
             "objective row is not counted in {n_cons}.", n_cons=mono("n_cons"))),
    ])

    primal = _dl([
        ("depth", "integer",
         "How deep in the branch-and-bound tree the node sits. The root is 0."),
        ("branch_var, branch_var_name", "integer, string",
         fmt("The branched column, as a 0-based index into the published file and as "
             "the name that file gives it. Prefer the name: on some instances a "
             "column is literally called {x91} while sitting at index 90, so an index "
             "read as a name points at the wrong variable.", x91=mono("x91"))),
        ("branch_sense, branch_value", "string, number",
         fmt("The bound that defines this side of the branch. {ours} means the search "
             "took {taken} and this file is the other side.",
             ours=mono(">=" + NBSP + "29"), taken=mono("<=" + NBSP + "28"))),
        ("path_entries", "list of strings",
         fmt("Every bound the node tightens relative to the source instance, written "
             "{form}. The index is 0-based into the published file, which {flag} "
             "records. This is the node's whole bound box, not only the branch "
             "decisions on the path to it, so it is usually far longer than the "
             "depth.", form=mono("x<index><=<value>"),
             flag=mono("path_entries_are_column_indices"))),
        ("path_head_named", "list of strings",
         "The first twelve entries with the column names resolved, which is what "
         "the page shows."),
    ])

    dual = _dl([
        ("n_dropped", "integer",
         fmt("How many elements were removed from the source relaxation. {natural} "
             "instances have zero: their relaxation was already unbounded.",
             natural=mono("natural_unbounded"))),
        ("drops[]", "list of objects",
         fmt("One entry per removal. A bound drop carries {kb}, the column as {var} "
             "(0-based index) and {name}, which {side} was relaxed, and the {value} "
             "it held. A row drop carries {kr}, the row index and name, and the "
             "{sense}, {rhs} and {rng} it had. <b>A dropped row's coefficients are "
             "not recorded</b>: restoring one means taking the row from the source "
             "instance.",
             kb=mono("kind: bound"), var=mono("var"), name=mono("name"),
             side=mono("side"), value=mono("original_value"), kr=mono("kind: row"),
             sense=mono("original_sense"), rhs=mono("original_rhs"),
             rng=mono("original_range"))),
        ("natural_unbounded", "boolean",
         "True when the source relaxation was already unbounded and nothing was "
         "removed."),
    ])

    internal = _dl([
        ("sample_id, schema_version, size", "various",
         fmt("Left over from the mining pipeline. {sid} indexes the candidate pool "
             "the published file was drawn from, not this collection; {size} is "
             "MIPLIB's own difficulty class for the source and says nothing about "
             "the published file.", sid=mono("sample_id"), size=mono("size"))),
        ("parent_uid, parent_depth", "integer",
         fmt("Solver-internal node identifiers from the run that produced the file. "
             "{pd} is always {expr}.", pd=mono("parent_depth"),
             expr=mono("depth - 1"))),
        ("beta, n_rounds, picks, seed", "various",
         fmt("Parameters and the pre-pruning trace of the greedy search behind a "
             "dual-infeasible file. {picks} lists what the search removed before the "
             "pruning pass put most of it back, so it is much longer than {drops} "
             "and is not the published removal set.",
             picks=mono("picks"), drops=mono("drops"))),
    ])

    body = fmt(GUIDE, common=common, primal=primal, dual=dual, internal=internal)
    return page("Reading a file", body, active="guide", depth=1, narrow=True)


def render_download(totals: dict, release_base_url: str | None = None,
                    sizes: dict[str, int] | None = None) -> str:
    """Download page: the links themselves.

    Args:
        totals (dict): collection aggregates.
        release_base_url (str | None): release download prefix. Without it the
            archive buttons render as disabled placeholders.
        sizes (dict | None): subset -> bytes of both files, from load.subset_bytes.
            Without it the page quotes no size rather than a wrong one.
    """
    sizes = sizes or {}
    base = release_base_url.rstrip("/") if release_base_url else None
    cards = []
    for subset, info in SUBSET_META.items():
        slug = info["slug"]
        size = fmt_bytes(sizes[subset]) if subset in sizes else ""
        label = join((f"{slug}.zip", el("span", size, class_="sz")))
        zip_btn = (el("a", label, class_="btn", href=f"{base}/{slug}.zip") if base
                   else el("span", label, class_="btn", aria_disabled="true"))
        cards.append(fmt(CARD, label=info["label"], slug=slug, tone=info["tone"],
                         d=info["dir"], zip_btn=zip_btn))

    in_all = f", {fmt_bytes(sum(sizes.values()))} in all" if sizes else ""
    body = fmt(DOWNLOAD, n_samples=fmt_int(totals["n_samples"]), in_all=in_all,
               cards=join(cards))
    return page("Download", body, active="download", depth=1, narrow=True)


def render_about() -> str:
    """About page: how the instances were produced, provenance, licence, citation."""
    return page("About", Markup(ABOUT), active="about", depth=1, narrow=True)
