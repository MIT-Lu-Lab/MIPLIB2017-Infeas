"""A single published instance: its dimensions, provenance and downloads."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .. import content, diagrams
from ..domain import SUBSET_SPECS, Drop, PrimalProvenance, Sample
from ..urls import rel
from .shell import page

_URL = re.compile("https?://[^\\s<>\"']+")


def _source_tokens(text: str) -> tuple[tuple[str, str | None], ...]:
    """Turn trusted URL-shaped spans into links while leaving all prose as text."""

    for source, replacement in (
        (r"\(i\)", "(i)"),
        (r"\(ii\)", "(ii)"),
        (r"\(n\times n\)", "n \N{MULTIPLICATION SIGN} n"),
        (r"\(n \le 61\)", "n \N{LESS-THAN OR EQUAL TO} 61"),
    ):
        text = text.replace(source, replacement)

    tokens: list[tuple[str, str | None]] = []
    start = 0
    for match in _URL.finditer(text):
        raw = match.group(0)
        url = raw.rstrip(".,;:!?)]")
        if match.start() > start:
            tokens.append((text[start : match.start()], None))
        tokens.append((url, url))
        if suffix := raw[len(url) :]:
            tokens.append((suffix, None))
        start = match.end()
    if start < len(text):
        tokens.append((text[start:], None))
    return tuple(tokens)


def _drop_label(drop: Drop) -> str:
    if drop["kind"] == "row":
        return "row " + str(drop.get("name") or drop["row"])
    return f"{drop['side']} of " + str(drop.get("name") or f"column {drop['var']}")


def _entry_count(total: int) -> str:
    return f"{content.fmt_int(total)} {'entry' if total == 1 else 'entries'}"


def render_sample(
    sample: Sample,
    cross: Sample | None,
    site_url: str | None = None,
    release_base_url: str | None = None,
    *,
    samples: Sequence[Sample] = (),
) -> str:
    """Render one sample page; ``cross`` is its counterpart in the other subset."""

    info = SUBSET_SPECS[sample.subset]
    here = sample.page_path + "index.html"
    provenance = sample.provenance
    details: dict[str, object]
    if isinstance(provenance, PrimalProvenance):
        value = int(provenance.branch_value)
        taken_sense, taken_value = (
            ("\N{LESS-THAN OR EQUAL TO}", value - 1)
            if provenance.branch_sense == ">="
            else ("\N{GREATER-THAN OR EQUAL TO}", value + 1)
        )
        details = {
            "branch": {
                "var": provenance.branch_label,
                "taken_sense": taken_sense,
                "taken_value": content.fmt_int(taken_value),
                "sense": (
                    "\N{GREATER-THAN OR EQUAL TO}"
                    if provenance.branch_sense == ">="
                    else "\N{LESS-THAN OR EQUAL TO}"
                ),
                "value": content.fmt_int(value),
            },
            "depth": content.fmt_int(provenance.depth),
            "bound_changes": content.fmt_int(provenance.bound_changes),
            "path_shown": content.fmt_int(len(provenance.path_head)),
            "path_count": _entry_count(provenance.bound_changes),
        }
    else:
        details = {
            "bounds_dropped": content.fmt_int(provenance.bounds_dropped),
            "rows_dropped": content.fmt_int(provenance.rows_dropped),
            "drops_shown": content.fmt_int(len(provenance.drops_head)),
            "total_dropped": content.fmt_int(provenance.total_dropped),
            "drop_count": _entry_count(provenance.total_dropped),
            "drop_labels": tuple(_drop_label(drop) for drop in provenance.drops_head),
        }

    prefix = f"{release_base_url}/" if release_base_url else None
    source_rows = [("Name", sample.instance)]
    if sample.submitter:
        source_rows.append(("Submitted by", sample.submitter))
    if sample.source_group:
        source_rows.append(("Group", sample.source_group))
    terms, terms_url = sample.source_terms_display
    cross_info = SUBSET_SPECS[cross.subset] if cross else None

    return page(
        "instance.html",
        f"{sample.instance} ({info.label.lower()})",
        active=sample.subset,
        page_rel=here,
        description=content.instance_description(
            sample.instance, info.label, sample.n_vars, sample.n_cons
        ),
        site_url=site_url,
        sample=sample,
        info=info,
        provenance=provenance,
        primal=isinstance(provenance, PrimalProvenance),
        up_href=rel(here, info.slug + "/"),
        n_vars=content.fmt_int(sample.n_vars),
        n_cons=content.fmt_int(sample.n_cons),
        nnz=content.fmt_int(sample.nnz),
        cross_info=cross_info,
        cross_href=rel(here, cross.page_path) if cross else None,
        downloads=tuple(
            {
                "name": name,
                "size": content.fmt_bytes(size),
                "href": prefix + name if prefix else None,
                "ghost": ghost,
            }
            for name, size, ghost in (
                (sample.stem + ".mps.gz", sample.file_bytes, False),
                (sample.stem + ".meta.json", sample.meta_bytes, True),
            )
        ),
        source_rows=tuple(source_rows),
        terms=terms,
        terms_url=terms_url,
        licence_href=rel(here, "LICENSE.txt"),
        shown_tags=tuple(tag for tag in sample.tags if tag not in content.NON_LP_TAGS),
        source_tokens=_source_tokens(sample.source_description or ""),
        details=details,
        # the collection with this instance marked, and the operation that
        # produced it: both drawn from what the page already states
        cloud=diagrams.cloud(samples or (sample,), here, sample, linked=False),
        derivation=(
            diagrams.branch_diagram(sample)
            if isinstance(provenance, PrimalProvenance)
            else diagrams.drops_diagram(sample)
        ),
    )
