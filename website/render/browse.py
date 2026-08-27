"""One subset's browse page: the facet rail and the sortable table."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .. import content
from ..facets import Facet, facets_for, row_values
from ..records import SUBSET_META, Sample, fmt_bytes, fmt_int
from .shell import Markup, el, fmt, join, json_script, page


@dataclass(frozen=True)
class Column:
    """One data column: its heading, the row field it shows, and how it reads.

    The field is the same name the facets use, so a column and a filter over it
    cannot end up reading two different numbers.
    """

    label: str
    field: str
    format: Callable[[int], str] = fmt_int


# Variables, Constraints and Nonzeros describe any linear program, so both
# subsets share one definition.
_COMMON_COLUMNS = (
    Column("Variables", "n_vars"),
    Column("Constraints", "n_cons"),
    Column("Nonzeros", "nnz"),
)
_FILE_COLUMN = Column("File", "file_bytes", fmt_bytes)

COLUMNS: dict[str, tuple[Column, ...]] = {
    "primal": (
        *_COMMON_COLUMNS,
        Column("Depth", "depth"),
        Column("Bounds tightened", "bound_changes"),
        _FILE_COLUMN,
    ),
    "dual": (
        *_COMMON_COLUMNS,
        Column("Bounds dropped", "bounds_dropped"),
        Column("Rows dropped", "rows_dropped"),
        _FILE_COLUMN,
    ),
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
    <!-- hidden until the script that makes it work has run: a search field that
         does nothing is worse than none -->
    <div class="table-search" hidden>
      <label class="sr-only" for="instance-search">Search instances by name</label>
      <input type="search" id="instance-search" class="search-input"
        placeholder="Search by name" autocomplete="off" spellcheck="false">
    </div>
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
{data}
"""


def _facet_rail(facets: list[Facet], rows: list[dict]) -> Markup:
    """The rail, with each bucket's count taken over the rows it will filter."""
    def group(facet: Facet) -> Markup:
        items = join(
            el("label",
               el("input", type_="checkbox", data_k=facet.key(bucket)),
               f" {bucket.label} ",
               el("span", sum(1 for values in rows if facet.holds(bucket, values)),
                  class_="n"))
            for bucket in facet.buckets)
        return el("fieldset", el("legend", facet.label, class_="eyebrow"), items,
                  class_="facet")

    return el("details",
              el("summary",
                 el("span", "Filters"),
                 el("span", "None selected", class_="facet-selected")),
              el("div", join(group(facet) for facet in facets),
                 class_="facet-groups"),
              class_="facets", open=True)


def _header(columns: tuple[Column, ...]) -> Markup:
    def sortable(label: str, field: str, right: bool = False) -> Markup:
        button = el("button", label, type_="button", class_="sort-button",
                    data_sort=field, aria_label=f"Sort by {label.lower()}")
        return el("th", button, scope="col", class_="r" if right else None)

    return join((
        sortable("Instance", "instance"),
        join(sortable(column.label, column.field, right=True) for column in columns),
        el("th", "Download", scope="col"),
    ))


def _row(sample: Sample, values: dict, columns: tuple[Column, ...]) -> Markup:
    cells = join(el("td", column.format(values[column.field]), class_="num")
                 for column in columns)
    name = values["instance"]
    dl_label = f"Download {name} as gzipped MPS"
    dl = (el("a", ".mps.gz", class_="dl", href=sample.mps_url,
             aria_label=dl_label) if sample.mps_url
          else el("span", "pending", class_="dl", role="link",
                  aria_disabled="true", aria_label=f"{dl_label}: unavailable"))
    return el("tr",
              el("th", el("a", name, href=f"{name}/"), scope="row", class_="name"),
              cells,
              el("td", dl))


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
    values = [row_values(s) for s in rows]
    columns = COLUMNS[subset]
    facets = facets_for(subset, values)
    body = fmt(
        BROWSE,
        label=info["label"],
        blurb=content.SUBSET_SUMMARY[subset],
        table_id=f"{info['slug']}-table-caption",
        archive=_archive_link(subset, rows, release_base_url),
        rail=_facet_rail(facets, values),
        header=_header(columns),
        rows=join(_row(s, v, columns) for s, v in zip(rows, values, strict=True)),
        data=json_script({"facets": [f.as_json() for f in facets], "rows": values},
                         id="browse-data", type="application/json"),
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
