"""A single published instance: its dimensions, provenance and downloads."""

from __future__ import annotations

from .. import content
from ..records import (NON_LP_TAGS, SUBSET_META, DualProvenance,
                       PrimalProvenance, Sample, fmt_bytes, fmt_int)
from .shell import Markup, el, fmt, join, page

DOWNLOAD_CARD = """<div class="card">
  <header><span class="eyebrow">Download</span></header>
  <div class="body">
    {mps}
    {meta}
    <p class="hint">The sidecar carries the full provenance, including the fields this
    page truncates.</p>
  </div>
</div>"""

SOURCE_CARD = """<div class="card">
  <header><span class="eyebrow">Source instance</span></header>
  <div class="body">
    {body}
    <a class="extlink" href="{url}" target="_blank" rel="noopener">
      View on MIPLIB 2017 →</a>
  </div>
</div>"""

RECIPE = """<div class="recipe">
<span class="k">branch taken by the search</span><br>
{var} {taken_sense} {taken_value}<br>
<span class="k">this instance, the other side</span><br>
<b>{var} {sense} {value}</b>
<span class="k">at depth {depth}</span></div>"""

PRIMAL_LEDE = """
    <p class="lede">A branch-and-bound run
    reached this node's parent and split on a variable. This instance is the side the
    search did not explore, and it has no feasible point.</p>
    {recipe}
    {kv}
  """

NATURAL_LEDE = ("<p class=\"lede\">The source instance's LP relaxation is "
                "unbounded as given. Nothing was removed to produce this "
                "instance.</p>")

DUAL_LEDE = """
    <p class="lede">The source instance's LP
    relaxation is feasible with a bounded optimum. Removing the elements below makes the
    objective unbounded, and putting any one of them back makes it bounded again.</p>
    {kv}
  """

DETAIL = """
<div class="detail-head">
  <div class="crumb"><a href="../">{subset}</a> / {instance}</div>
  <h1>{instance}</h1>
  <div class="badges">{badges}</div>
</div>
<div class="detail">
  <div>
    {instance_panel}
    {panels}
    {crosslink}
  </div>
  <div class="aside">{aside}</div>
</div>
"""


def _kv(pairs) -> Markup:
    return el("dl", join(join((el("dt", k), el("dd", v))) for k, v in pairs),
              class_="kv")


def _entries(labels) -> Markup:
    """The scrolling provenance list shared by both subsets."""
    return el("div", join(el("span", x) for x in labels), class_="path")


def _panel(title: str, eyebrow: str, body: Markup) -> Markup:
    return el("div",
              el("header", el("h2", title), el("span", eyebrow, class_="eyebrow")),
              el("div", body, class_="body"),
              class_="panel")


def _shown_of(shown: int, total: int) -> Markup:
    return el("p", f"{fmt_int(shown)} of {fmt_int(total)} shown. "
                   "The complete list is in the sidecar.", class_="more")


def _download_card(sample: Sample) -> Markup:
    def btn(url: str | None, name: str, size: str, ghost: bool = False) -> Markup:
        cls = "btn ghost" if ghost else "btn"
        label = join((el("span", name, class_="btn-label"),
                      el("span", size, class_="sz")))
        if not url:
            return el("span", label, class_=cls, aria_disabled="true")
        return el("a", label, class_=cls, href=url)

    return fmt(
        DOWNLOAD_CARD,
        mps=btn(sample.mps_url, sample.stem + ".mps.gz", fmt_bytes(sample.file_bytes)),
        meta=btn(sample.meta_url, sample.stem + ".meta.json",
                 fmt_bytes(sample.meta_bytes), ghost=True),
    )


def _source_card(sample: Sample) -> Markup:
    """The MIPLIB instance this one derives from, and who contributed it.

    CC BY-SA 4.0 requires adapted material to identify the creator of the
    original, so the submitter is an attribution obligation rather than a
    convenience. The description is MIPLIB's own prose and is labelled as such.
    """
    rows = [("Name", sample.instance)]
    if sample.submitter:
        rows.append(("Submitted by", sample.submitter))
    if sample.source_group:
        rows.append(("Group", sample.source_group))
    parts = [el("div", el("span", k), el("span", v), class_="src-row")
             for k, v in rows]

    shown = [t for t in sample.tags if t not in NON_LP_TAGS]
    if shown:
        parts.append(el("div", join(el("span", t, class_="srctag") for t in shown),
                        class_="srctags"))
    if sample.source_description:
        parts.append(el("p", sample.source_description, class_="hint"))
        parts.append(el("p", "Description from MIPLIB 2017.", class_="hint credit"))

    return fmt(SOURCE_CARD, body=join(parts), url=sample.miplib_url)


def _primal_panels(p: PrimalProvenance) -> Markup:
    value = int(p.branch_value)
    # the search took one side of an integer split; this instance is the other, so
    # its bound sits one integer step away in the opposite direction
    taken_sense, taken_value = ("≤", value - 1) if p.branch_sense == ">=" \
        else ("≥", value + 1)
    sense = "≥" if p.branch_sense == ">=" else "≤"
    recipe = fmt(RECIPE, var=p.branch_label, taken_sense=taken_sense,
                 taken_value=fmt_int(taken_value), sense=sense,
                 value=fmt_int(value), depth=fmt_int(p.depth))
    return join((
        _panel("Where it comes from", "provenance",
               fmt(PRIMAL_LEDE, recipe=recipe, kv=_kv([
                   ("Depth in the tree", fmt_int(p.depth)),
                   ("Bounds tightened vs. source", fmt_int(p.bound_changes)),
                   ("Branch variable", p.branch_label)]))),
        _panel("Tightened bounds", f"{fmt_int(p.bound_changes)} entries",
               join((_entries(p.path_head),
                     _shown_of(len(p.path_head), p.bound_changes)))),
    ))


def _drop_label(d: dict) -> str:
    """One removed element, as the sidecar records it.

    Rows and bounds are named the same way: by column or row name when the miner
    resolved one, and by index when it did not.
    """
    if d["kind"] == "row":
        return "row " + str(d.get("name") or d["row"])
    return f'{d["side"]} of ' + str(d.get("name") or f'column {d["var"]}')


def _dual_panels(p: DualProvenance) -> Markup:
    if p.natural_unbounded:
        return _panel("Where it comes from", "provenance", Markup(NATURAL_LEDE))
    return join((
        _panel("Where it comes from", "provenance",
               fmt(DUAL_LEDE, kv=_kv([("Bounds dropped", fmt_int(p.bounds_dropped)),
                                      ("Rows dropped", fmt_int(p.rows_dropped))]))),
        _panel("What was removed", f"{fmt_int(p.total_dropped)} entries",
               join((_entries(_drop_label(d) for d in p.drops_head),
                     _shown_of(len(p.drops_head), p.total_dropped)))),
    ))


def render_sample(sample: Sample, cross: Sample | None,
                  canonical: str | None = None) -> str:
    """One sample page. `cross` is the same instance in the other subset, or None."""
    info = SUBSET_META[sample.subset]
    provenance = sample.provenance
    badges = [el("span", info["label"].lower(), class_=f'badge {info["tone"]}')]
    if isinstance(provenance, DualProvenance):
        panels = _dual_panels(provenance)
        if provenance.natural_unbounded:
            badges.append(el("span", "unbounded as given", class_="badge n"))
    else:
        panels = _primal_panels(provenance)

    crosslink = Markup("")
    if cross is not None:
        other = SUBSET_META[cross.subset]
        crosslink = el(
            "a",
            el("span", "Also published in the ",
               el("b", other["label"].lower()), " set"),
            el("span", "view →", class_="mono"),
            class_=f'crosslink {other["tone"]}',
            href=f"../../{cross.page_path}")

    body = fmt(
        DETAIL,
        subset=info["label"],
        instance=sample.instance,
        badges=join(badges),
        instance_panel=_panel("The instance", "as published", _kv([
            ("Variables", fmt_int(sample.n_vars)),
            ("Constraints", fmt_int(sample.n_cons)),
            ("Nonzeros", fmt_int(sample.nnz)),
            ("Format", "MPS, gzipped")])),
        panels=panels,
        crosslink=crosslink,
        aside=join((_download_card(sample), _source_card(sample))),
    )
    return page(f"{sample.instance} ({info['label'].lower()})", body,
                active=sample.subset, depth=2,
                description=content.instance_description(
                    sample.instance, info["label"], sample.n_vars, sample.n_cons),
                canonical=canonical)
