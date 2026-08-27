"""One subset's browse page: the facet rail and the sortable table."""

from __future__ import annotations

from .. import content
from ..records import NON_LP_TAGS, SUBSET_META, Sample, fmt_bytes, fmt_int
from .shell import Markup, el, fmt, join, page


# A facet group is (label, [(option label, key, predicate)]). The key is what the
# client-side filter matches; it ships as a `data-f` token on every row, so it must
# not change once published.
# Variables and Constraints describe any LP, so both subsets share one definition
# rather than each carrying its own copy that could drift.
_SIZE_FACETS = [
    ("Variables", [
        ("under 50 K", "vars-lt50k", lambda s: s.n_vars < 50_000),
        ("50 K – 500 K", "vars-50k-500k", lambda s: 50_000 <= s.n_vars < 500_000),
        ("over 500 K", "vars-gt500k", lambda s: s.n_vars >= 500_000)]),
    ("Constraints", [
        ("under 10 K", "cons-lt10k", lambda s: s.n_cons < 10_000),
        ("10 K – 100 K", "cons-10k-100k", lambda s: 10_000 <= s.n_cons < 100_000),
        ("over 100 K", "cons-gt100k", lambda s: s.n_cons >= 100_000)]),
]

FACETS = {
    "primal": [
        *_SIZE_FACETS,
        ("Depth", [
            ("under 50", "depth-lt50", lambda s: s.primal.depth < 50),
            ("50 – 250", "depth-50-250", lambda s: 50 <= s.primal.depth < 250),
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
            ("1 – 5 elements", "size-1-5",
             lambda s: 1 <= s.dual.total_dropped <= 5),
            ("6 – 50", "size-6-50", lambda s: 6 <= s.dual.total_dropped <= 50),
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

BROWSE = """
<div class="browse-head">
  <div>
    <span class="eyebrow">Subset</span>
    <h1>{label}</h1>
    <p class="desc">{blurb}</p>
  </div>
  {archive}
</div>
<div class="browse">
  {rail}
  <div>
    <div class="table-wrap" tabindex="0" role="region" aria-labelledby="{table_id}"><table>
      <caption id="{table_id}" class="sr-only">{label} instances</caption>
      <thead><tr>{header}</tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
    <p class="table-foot"><span class="result-count" data-total="{total}"
      role="status" aria-live="polite" aria-atomic="true">{total_label}.</span>
      All data columns sort; Download does not.</p>
  </div>
</div>
"""


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


def _facet_rail(groups: list[tuple], rows: list[Sample]) -> Markup:
    def group(label: str, options) -> Markup:
        items = join(
            el("label",
               el("input", type_="checkbox", data_k=key),
               f" {opt} ",
               el("span", sum(1 for s in rows if pred(s)), class_="n"))
            for opt, key, pred in options)
        return el("fieldset", el("legend", label, class_="eyebrow"), items,
                  class_="facet")

    return el("details",
              el("summary",
                 el("span", "Filters"),
                 el("span", "None selected", class_="facet-selected")),
              el("div", join(group(label, options) for label, options in groups),
                 class_="facet-groups"),
              class_="facets", open=True)


def _header(cols: list[tuple]) -> Markup:
    def sortable(label: str, kind: str, right: bool = False) -> Markup:
        button = el("button", label, type_="button", class_="sort-button",
                    data_sort=kind, aria_label=f"Sort by {label.lower()}")
        return el("th", button, scope="col", class_="r" if right else None)

    return join((
        sortable("Instance", "str"),
        join(sortable(h, "num", right=True) for h, _ in cols),
        el("th", "Download", scope="col"),
    ))


def _row(s: Sample, cols: list[tuple], groups: list[tuple]) -> Markup:
    cells = join(el("td", disp, class_="num", data_v=v)
                 for v, disp in (acc(s) for _, acc in cols))
    dl_label = f"Download {s.instance} as gzipped MPS"
    dl = (el("a", ".mps.gz", class_="dl", href=s.mps_url,
             aria_label=dl_label) if s.mps_url
          else el("span", "pending", class_="dl", role="link",
                  aria_disabled="true", aria_label=f"{dl_label}: unavailable"))
    return el("tr",
              el("th", el("a", s.instance, href=f"{s.instance}/"),
                 scope="row", class_="name", data_v=s.instance),
              cells,
              el("td", dl),
              data_f=" ".join(_row_facet_keys(groups, s)))


def _archive_link(subset: str, rows: list[Sample],
                  release_base_url: str | None) -> Markup:
    """The whole-subset download. Its size counts both files of every instance, so it
    is not the .mps.gz total the File column sums to."""
    count = f"{fmt_int(len(rows))} {'instance' if len(rows) == 1 else 'instances'}"
    label = f"{count}, {fmt_bytes(sum(s.total_bytes for s in rows))} unpacked"
    if not release_base_url:
        return el("span", label, class_="dl", role="link", aria_disabled="true",
                  aria_label=f"{SUBSET_META[subset]['label']} archive: unavailable")
    href = f'{release_base_url.rstrip("/")}/{SUBSET_META[subset]["slug"]}.zip'
    return el("a", f"{label} ↓", class_="dl", href=href)


def page_rel(subset: str) -> str:
    """Where this subset's browse page goes, and what its links resolve from."""
    return f"{SUBSET_META[subset]['slug']}/index.html"


def render_browse(subset: str, samples: list[Sample],
                  release_base_url: str | None = None,
                  site_url: str | None = None) -> str:
    """One subset's browse page: facet rail plus a sortable table."""
    info = SUBSET_META[subset]
    rows = [s for s in samples if s.subset == subset]
    cols = COLUMNS[subset]
    groups = facet_groups(subset, rows)
    body = fmt(
        BROWSE,
        label=info["label"],
        blurb=content.SUBSET_SUMMARY[subset],
        table_id=f"{info['slug']}-table-caption",
        archive=_archive_link(subset, rows, release_base_url),
        rail=_facet_rail(groups, rows),
        header=_header(cols),
        rows=join(_row(s, cols, groups) for s in rows),
        total=len(rows),
        total_label=(f"{fmt_int(len(rows))} "
                     f"{'instance' if len(rows) == 1 else 'instances'}"),
    )
    return page(f"{info['label']} instances", body, active=subset,
                page_rel=page_rel(subset),
                description=content.subset_description(
                    subset, len(rows),
                    sum(s.dual.natural_unbounded for s in rows)
                    if subset == "dual" else 0),
                site_url=site_url)
