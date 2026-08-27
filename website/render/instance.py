"""A single published instance: its dimensions, provenance and downloads."""

from __future__ import annotations

from ..records import (NON_LP_TAGS, SUBSET_META, DualProvenance,
                       PrimalProvenance, Sample, fmt_bytes, fmt_int)
from .shell import esc, page


def _kv(pairs) -> str:
    return ('<dl class="kv">'
            + "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in pairs)
            + "</dl>")


def _entries(labels) -> str:
    """The scrolling provenance list shared by both subsets."""
    return f'<div class="path">{"".join(f"<span>{esc(x)}</span>" for x in labels)}</div>'


def _panel(title: str, eyebrow: str, body: str) -> str:
    return (f'<div class="panel"><header><h2>{esc(title)}</h2>'
            f'<span class="eyebrow">{esc(eyebrow)}</span></header>'
            f'<div class="body">{body}</div></div>')


def _shown_of(shown: int, total: int) -> str:
    return (f'<p class="more">{fmt_int(shown)} of {fmt_int(total)} shown. '
            "The complete list is in the sidecar.</p>")


def _download_card(sample: Sample) -> str:
    def btn(url: str | None, name: str, size: str, ghost: bool = False) -> str:
        cls = "btn ghost" if ghost else "btn"
        if not url:
            return (f'<span class="{cls}" aria-disabled="true">{esc(name)}'
                    f'<span class="sz">{size}</span></span>')
        return (f'<a class="{cls}" href="{esc(url)}">{esc(name)}'
                f'<span class="sz">{size}</span></a>')
    return f"""<div class="card">
  <header><span class="eyebrow">Download</span></header>
  <div class="body">
    {btn(sample.mps_url, sample.stem + ".mps.gz", fmt_bytes(sample.file_bytes))}
    {btn(sample.meta_url, sample.stem + ".meta.json", fmt_bytes(sample.meta_bytes), ghost=True)}
    <p class="hint">The sidecar carries the full provenance, including the fields this
    page truncates.</p>
  </div>
</div>"""


def _source_card(sample: Sample) -> str:
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
    body = "".join(f'<div class="src-row"><span>{esc(k)}</span><span>{esc(v)}</span></div>'
                   for k, v in rows)

    shown = [t for t in sample.tags if t not in NON_LP_TAGS]
    if shown:
        body += ('<div class="srctags">'
                 + "".join(f'<span class="srctag">{esc(t)}</span>' for t in shown)
                 + "</div>")
    if sample.source_description:
        body += (f'<p class="hint">{esc(sample.source_description)}</p>'
                 '<p class="hint credit">Description from MIPLIB 2017.</p>')

    return f"""<div class="card">
  <header><span class="eyebrow">Source instance</span></header>
  <div class="body">
    {body}
    <a class="extlink" href="{esc(sample.miplib_url)}" target="_blank" rel="noopener">
      View on MIPLIB 2017 &rarr;</a>
  </div>
</div>"""


def _primal_panels(p: PrimalProvenance) -> str:
    var = esc(p.branch_label)
    value = int(p.branch_value)
    # the search took one side of an integer split; this instance is the other, so
    # its bound sits one integer step away in the opposite direction
    taken_sense, taken_val = ("&le;", value - 1) if p.branch_sense == ">=" else ("&ge;", value + 1)
    mine = "&ge;" if p.branch_sense == ">=" else "&le;"
    recipe = f"""<div class="recipe">
<span class="k">branch taken by the search</span><br>
{var} {taken_sense} {fmt_int(taken_val)}<br>
<span class="k">this instance, the other side</span><br>
<b>{var} {mine} {fmt_int(value)}</b>
<span class="k">at depth {fmt_int(p.depth)}</span></div>"""
    return _panel("Where it comes from", "provenance", f"""
    <p class="lede">A branch-and-bound run
    reached this node's parent and split on a variable. This instance is the side the
    search did not explore, and it has no feasible point.</p>
    {recipe}
    {_kv([("Depth in the tree", fmt_int(p.depth)),
          ("Bounds tightened vs. source", fmt_int(p.bound_changes)),
          ("Branch variable", var)])}
  """) + _panel(
        "Tightened bounds", f"{fmt_int(p.bound_changes)} entries",
        _entries(p.path_head) + _shown_of(len(p.path_head), p.bound_changes))


def _drop_label(d: dict) -> str:
    """One removed element, as the sidecar records it.

    Rows and bounds are named the same way: by column or row name when the miner
    resolved one, and by index when it did not.
    """
    if d["kind"] == "row":
        return "row " + str(d.get("name") or d["row"])
    return f'{d["side"]} of ' + str(d.get("name") or f'column {d["var"]}')


def _dual_panels(p: DualProvenance) -> str:
    total = p.total_dropped
    if p.natural_unbounded:
        return _panel("Where it comes from", "provenance",
                      '<p class="lede">The source '
                      "instance's LP relaxation is unbounded as given. Nothing was removed to "
                      "produce this instance.</p>")
    return _panel("Where it comes from", "provenance", f"""
    <p class="lede">The source instance's LP
    relaxation is feasible with a bounded optimum. Removing the elements below makes the
    objective unbounded, and putting any one of them back makes it bounded again.</p>
    {_kv([("Bounds dropped", fmt_int(p.bounds_dropped)),
          ("Rows dropped", fmt_int(p.rows_dropped))])}
  """) + _panel(
        "What was removed", f"{fmt_int(total)} entries",
        _entries(_drop_label(d) for d in p.drops_head)
        + _shown_of(len(p.drops_head), total))


def render_sample(sample: Sample, cross: Sample | None) -> str:
    """One sample page. `cross` is the same instance in the other subset, or None."""
    info = SUBSET_META[sample.subset]
    provenance = sample.provenance
    badges = [f'<span class="badge {info["tone"]}">{esc(info["label"].lower())}</span>']
    if isinstance(provenance, DualProvenance):
        panels = _dual_panels(provenance)
        if provenance.natural_unbounded:
            badges.append('<span class="badge n">unbounded as given</span>')
    else:
        panels = _primal_panels(provenance)

    crosslink = ""
    if cross is not None:
        other = SUBSET_META[cross.subset]
        crosslink = (
            f'<a class="crosslink {other["tone"]}" href="../../{esc(cross.page_path)}">'
            f'<span>Also published in the <b>{esc(other["label"].lower())}</b> set</span>'
            f'<span class="mono">view &rarr;</span></a>')

    body = f"""
<div class="detail-head">
  <div class="crumb"><a href="../">{esc(info['label'])}</a> / {esc(sample.instance)}</div>
  <h1>{esc(sample.instance)}</h1>
  <div class="badges">{"".join(badges)}</div>
</div>
<div class="detail">
  <div>
    {_panel("The instance", "as published", _kv([
        ("Variables", fmt_int(sample.n_vars)),
        ("Constraints", fmt_int(sample.n_cons)),
        ("Nonzeros", fmt_int(sample.nnz)),
        ("Format", "MPS, gzipped")]))}
    {panels}
    {crosslink}
  </div>
  <div class="aside">{_download_card(sample)}{_source_card(sample)}</div>
</div>
"""
    return page(f"{sample.instance} ({info['label'].lower()})", body,
                active=sample.subset, depth=2)
