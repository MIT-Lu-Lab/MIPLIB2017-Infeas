"""One subset's browse page: the facet rail and the sortable table."""

from __future__ import annotations

from ..records import NON_LP_TAGS, SUBSET_META, Sample, fmt_bytes, fmt_int
from .shell import esc, page


# A facet group is (label, [(option label, key, predicate)]). The key is what the
# client-side filter matches; it ships as a `data-f` token on every row, so it must
# not change once published.
# Variables and Constraints describe any LP, so both subsets share one definition
# rather than each carrying its own copy that could drift.
_SIZE_FACETS = [
    ("Variables", [
        ("under 50 K", "vars-lt50k", lambda s: s.n_vars < 50_000),
        ("50 K &ndash; 500 K", "vars-50k-500k", lambda s: 50_000 <= s.n_vars < 500_000),
        ("over 500 K", "vars-gt500k", lambda s: s.n_vars >= 500_000)]),
    ("Constraints", [
        ("under 10 K", "cons-lt10k", lambda s: s.n_cons < 10_000),
        ("10 K &ndash; 100 K", "cons-10k-100k", lambda s: 10_000 <= s.n_cons < 100_000),
        ("over 100 K", "cons-gt100k", lambda s: s.n_cons >= 100_000)]),
]

FACETS = {
    "primal": [
        *_SIZE_FACETS,
        ("Depth", [
            ("under 50", "depth-lt50", lambda s: s.primal.depth < 50),
            ("50 &ndash; 250", "depth-50-250", lambda s: 50 <= s.primal.depth < 250),
            ("over 250", "depth-gt250", lambda s: s.primal.depth >= 250)]),
    ],
    "dual": [
        *_SIZE_FACETS,
        ("What was relaxed", [
            ("variable bounds only", "relax-bounds-only",
             lambda s: s.dual.rows_dropped == 0 and s.dual.bounds_dropped > 0),
            ("bounds and constraints", "relax-bounds-rows",
             lambda s: s.dual.rows_dropped > 0),
            ("unbounded as given", "relax-natural",
             lambda s: s.dual.natural_unbounded)]),
        ("Relaxation size", [
            ("nothing removed", "size-0", lambda s: s.dual.total_dropped == 0),
            ("1 &ndash; 5 elements", "size-1-5",
             lambda s: 1 <= s.dual.total_dropped <= 5),
            ("6 &ndash; 50", "size-6-50", lambda s: 6 <= s.dual.total_dropped <= 50),
            ("over 50", "size-gt50", lambda s: s.dual.total_dropped > 50)]),
    ],
}

# tags come from MIPLIB and vary by subset, so this group is built from the rows in
# hand rather than hardcoded. Only tags carried by enough instances to narrow the
# table are worth a checkbox.
TAG_FACET_MIN = 8

# A column is (header, accessor returning (sort value, display text)). Every column
# sorts numerically; the instance name is rendered separately and sorts as a string.
_COMMON_COLUMNS = [
    ("Variables", lambda s: (s.n_vars, fmt_int(s.n_vars))),
    ("Constraints", lambda s: (s.n_cons, fmt_int(s.n_cons))),
    ("Nonzeros", lambda s: (s.nnz, fmt_int(s.nnz))),
]
_FILE_COLUMN = ("File", lambda s: (s.file_bytes, fmt_bytes(s.file_bytes)))

COLUMNS = {
    "primal": [
        *_COMMON_COLUMNS,
        ("Depth", lambda s: (s.primal.depth, fmt_int(s.primal.depth))),
        ("Bounds tightened",
         lambda s: (s.primal.bound_changes, fmt_int(s.primal.bound_changes))),
        _FILE_COLUMN,
    ],
    "dual": [
        *_COMMON_COLUMNS,
        ("Bounds dropped",
         lambda s: (s.dual.bounds_dropped, fmt_int(s.dual.bounds_dropped))),
        ("Rows dropped", lambda s: (s.dual.rows_dropped, fmt_int(s.dual.rows_dropped))),
        _FILE_COLUMN,
    ],
}

BROWSE_BLURB = {
    "primal": "Linear programs with no feasible point. Each one is a node that a "
              "branch-and-bound search reached and then pruned, on a distinct MIPLIB 2017 "
              "instance.",
    "dual": "Linear programs whose objective is unbounded, from MIPLIB 2017 root "
            "relaxations with a minimal set of bounds and constraints removed.",
}


def _tag_options(rows: list[Sample]) -> list[tuple]:
    counts = {}
    for s in rows:
        for t in s.tags:
            if t not in NON_LP_TAGS:
                counts[t] = counts.get(t, 0) + 1
    keep = sorted(((t, n) for t, n in counts.items() if n >= TAG_FACET_MIN),
                  key=lambda kv: (-kv[1], kv[0]))
    return [(t, f"tag-{t}", (lambda tag: lambda s: tag in s.tags)(t)) for t, _ in keep]


def facet_groups(subset: str, rows: list[Sample]) -> list[tuple]:
    """Every facet group these rows are offered, fixed ones first.

    The rail and the rows' `data-f` tokens are both derived from the returned list,
    so a filter can never count rows it cannot select.
    """
    opts = _tag_options(rows)
    return [*FACETS[subset], *([("Structure (MIPLIB)", opts)] if opts else [])]


def _row_facet_keys(groups: list[tuple], s: Sample) -> list[str]:
    return [key for _, options in groups for _, key, pred in options if pred(s)]


def _facet_rail(groups: list[tuple], rows: list[Sample]) -> str:
    rail = []
    for label, options in groups:
        items = "".join(
            f'<label><input type="checkbox" data-k="{key}"> {opt} '
            f'<span class="n">{sum(1 for s in rows if pred(s))}</span></label>'
            for opt, key, pred in options)
        rail.append(f'<div class="facet"><span class="eyebrow">{esc(label)}</span>{items}</div>')
    return f'<div class="facets">{"".join(rail)}</div>'


def _header(cols: list[tuple]) -> str:
    return ('<th data-sort="str" tabindex="0" role="button" '
            'aria-label="Sort by instance">Instance</th>'
            + "".join(f'<th class="r" data-sort="num" tabindex="0" role="button" '
                      f'aria-label="Sort by {esc(h.lower())}">{esc(h)}</th>'
                      for h, _ in cols)
            + "<th></th>")


def _row(s: Sample, cols: list[tuple], groups: list[tuple]) -> str:
    cells = "".join(f'<td class="num" data-v="{esc(v)}">{disp}</td>'
                    for v, disp in (acc(s) for _, acc in cols))
    dl = (f'<a class="dl" href="{esc(s.mps_url)}">.mps.gz</a>'
          if s.mps_url else '<span class="dl" aria-disabled="true">pending</span>')
    return (f'<tr data-f="{esc(" ".join(_row_facet_keys(groups, s)))}">'
            f'<td class="name" data-v="{esc(s.instance)}">'
            f'<a href="{esc(s.instance)}/">{esc(s.instance)}</a></td>'
            f"{cells}<td>{dl}</td></tr>")


def _archive_link(subset: str, rows: list[Sample], release_base_url: str | None) -> str:
    """The whole-subset download. Its size counts both files of every instance, so it
    is not the .mps.gz total the File column sums to."""
    label = f"{fmt_int(len(rows))} instances, {fmt_bytes(sum(s.total_bytes for s in rows))}"
    if not release_base_url:
        return f'<span class="dl" aria-disabled="true">{label}</span>'
    href = f'{release_base_url.rstrip("/")}/{SUBSET_META[subset]["slug"]}.zip'
    return f'<a class="dl" href="{esc(href)}">{label} &darr;</a>'


def render_browse(subset: str, samples: list[Sample],
                  release_base_url: str | None = None) -> str:
    """One subset's browse page: facet rail plus a sortable table."""
    info = SUBSET_META[subset]
    rows = [s for s in samples if s.subset == subset]
    cols = COLUMNS[subset]
    groups = facet_groups(subset, rows)
    body = f"""
<div class="browse-head">
  <div>
    <span class="eyebrow">Subset</span>
    <h1>{esc(info['label'])}</h1>
    <p class="desc">{esc(BROWSE_BLURB[subset])}</p>
  </div>
  {_archive_link(subset, rows, release_base_url)}
</div>
<div class="browse">
  {_facet_rail(groups, rows)}
  <div>
    <div class="table-wrap"><table>
      <thead><tr>{_header(cols)}</tr></thead>
      <tbody>{"".join(_row(s, cols, groups) for s in rows)}</tbody>
    </table></div>
    <p class="table-foot" data-total="{len(rows)}">{fmt_int(len(rows))} instances.
    Every column sorts.</p>
  </div>
</div>
"""
    return page(f"{info['label']} instances", body, active=subset, depth=1)
