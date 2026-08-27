"""Pages that do not vary with an instance: guide, download, about."""

from __future__ import annotations

from ..records import SUBSET_META, fmt_bytes, fmt_int
from .shell import esc, page


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


# U+00A0. Bound to a name because a backslash inside an f-string expression
# only became legal in Python 3.12, and the generator targets 3.10.
NBSP = "\u00a0"


def mono(text: str) -> str:
    """Code voice for a field name or a literal. Escapes, so callers pass text."""
    return f'<span class="mono">{esc(text)}</span>'


def _dl(rows) -> str:
    """A field reference block: name, type, and what it means."""
    return ('<dl class="fields">' + "".join(
        f'<dt><span class="mono">{esc(name)}</span>'
        f'<span class="ftype">{esc(kind)}</span></dt><dd>{body}</dd>'
        for name, kind, body in rows) + "</dl>")


def render_guide() -> str:
    """Reference for every field in a sidecar and every figure on a page.

    Without this a reader cannot tell that `drops[].var` is a 0-based column
    index, or that a dropped row's coefficients are not recorded, so the
    minimality claim is not checkable from what is published.
    """
    common = _dl([
        ("instance", "string",
         f"Name of the MIPLIB 2017 instance this one derives from. The published "
         f"file is that name plus {mono('_if')} or {mono('_ub')}."),
        ("sample_kind", "string",
         f"Which half the file belongs to: {mono('pruned_infeasible_sibling')} for "
         f"the primal set, {mono('lp_unbounded_after_drop')} for the dual one. The "
         f"first name is older than the wording on these pages and claims more than "
         f"the file records: what it holds is the side of a branch the search did "
         f"not explore."),
        ("n_vars, n_cons, nnz", "integer",
         f"Columns, rows and matrix nonzeros of the published file, counted from "
         f"the file itself rather than from the model that produced it. The "
         f"objective row is not counted in {mono('n_cons')}."),
    ])

    primal = _dl([
        ("depth", "integer",
         "How deep in the branch-and-bound tree the node sits. The root is 0."),
        ("branch_var, branch_var_name", "integer, string",
         f"The branched column, as a 0-based index into the published file and as "
         f"the name that file gives it. Prefer the name: on some instances a "
         f"column is literally called {mono('x91')} while sitting at index 90, so "
         f"an index read as a name points at the wrong variable."),
        ("branch_sense, branch_value", "string, number",
         f"The bound that defines this side of the branch. {mono('>=' + NBSP + '29')} means "
         f"the search took {mono('<=' + NBSP + '28')} and this file is the other side."),
        ("path_entries", "list of strings",
         f"Every bound the node tightens relative to the source instance, written "
         f"{mono('x<index><=<value>')}. The index is 0-based into the published "
         f"file, which {mono('path_entries_are_column_indices')} records. This is "
         f"the node's whole bound box, not only the branch decisions on the path to "
         f"it, so it is usually far longer than the depth."),
        ("path_head_named", "list of strings",
         "The first twelve entries with the column names resolved, which is what "
         "the page shows."),
    ])

    dual = _dl([
        ("n_dropped", "integer",
         f"How many elements were removed from the source relaxation. "
         f"{mono('natural_unbounded')} instances have zero: their relaxation was "
         f"already unbounded."),
        ("drops[]", "list of objects",
         f"One entry per removal. A bound drop carries {mono('kind: bound')}, the "
         f"column as {mono('var')} (0-based index) and {mono('name')}, which "
         f"{mono('side')} was relaxed, and the {mono('original_value')} it held. "
         f"A row drop carries {mono('kind: row')}, the row index and name, and the "
         f"{mono('original_sense')}, {mono('original_rhs')} and "
         f"{mono('original_range')} it had. <b>A dropped row's coefficients are "
         f"not recorded</b>: restoring one means taking the row from the source "
         f"instance."),
        ("natural_unbounded", "boolean",
         "True when the source relaxation was already unbounded and nothing was "
         "removed."),
    ])

    internal = _dl([
        ("sample_id, schema_version, size", "various",
         f"Left over from the mining pipeline. {mono('sample_id')} indexes the "
         f"candidate pool the published file was drawn from, not this collection; "
         f"{mono('size')} is MIPLIB's own difficulty class for the source and says "
         f"nothing about the published file."),
        ("parent_uid, parent_depth", "integer",
         f"Solver-internal node identifiers from the run that produced the file. "
         f"{mono('parent_depth')} is always {mono('depth - 1')}."),
        ("beta, n_rounds, picks, seed", "various",
         f"Parameters and the pre-pruning trace of the greedy search behind a "
         f"dual-infeasible file. {mono('picks')} lists what the search removed "
         f"before the pruning pass put most of it back, so it is much longer than "
         f"{mono('drops')} and is not the published removal set."),
    ])

    body = f"""
<div class="masthead">
  <span class="eyebrow">Reference</span>
  <h1>Reading a file</h1>
  <p class="sub">Every published instance is a gzipped MPS beside a
  <span class="mono">.meta.json</span> sidecar recording how it was derived. This page
  says what each field means and how to check the collection's claims yourself.</p>
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
        if base:
            zip_btn = (f'<a class="btn" href="{esc(base)}/{slug}.zip">{slug}.zip'
                       f'<span class="sz">{size}</span></a>')
        else:
            zip_btn = (f'<span class="btn" aria-disabled="true">{slug}.zip'
                       f'<span class="sz">{size}</span></span>')
        cards.append(CARD.format(label=esc(info["label"]), slug=slug, tone=info["tone"],
                                 d=info["dir"], zip_btn=zip_btn))

    in_all = f", {fmt_bytes(sum(sizes.values()))} in all" if sizes else ""
    body = f"""
<div class="masthead">
  <span class="eyebrow">Files</span>
  <h1>Download</h1>
  <p class="sub">{fmt_int(totals['n_samples'])} instances. The archives below carry both
  files of every instance{in_all}.</p>
</div>
<div class="pair">{"".join(cards)}</div>
<p class="note">Single instances download from
their own page. Every asset sits directly under the release prefix, so a filename taken
from an index is all you need to append.</p>
"""
    return page("Download", body, active="download", depth=1, narrow=True)


def render_about() -> str:
    """About page: how the instances were produced, provenance, licence, citation."""
    body = """
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
    return page("About", body, active="about", depth=1, narrow=True)
