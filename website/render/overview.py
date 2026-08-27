"""The site root."""

from __future__ import annotations

import json
from string import Template

from ..records import SUBSET_META, fmt_int
from .shell import Markup, el, esc, fmt, join, page

SUBSET_BLURB = {
    "primal": "A branch-and-bound run splits on a variable and explores one side of "
              "the split. This set collects the other side, at nodes where that side "
              "has no feasible point.",
    "dual": "Bounds and constraints are removed from a MIPLIB relaxation until the "
            "objective becomes unbounded, then every removal that proves unnecessary "
            "is restored.",
}

CARD = """<a class="subset {tone}" href="{slug}/">
      <h3>{label}</h3>
      <div class="count">{count} instances</div>
      <p>{blurb}</p>
      <span class="go">Browse them all →</span>
    </a>"""

# $-substitution, not braces: the entry is full of them and doubling every one to
# please a formatter is how the block became unreadable in the first place.
CITATION = Template("""@misc{miplib_infeas,<br>
    &nbsp;&nbsp;author&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {Haihao Lu and Bo Tang},<br>
    &nbsp;&nbsp;title&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {MIPLIB-Infeas: Primal- and Dual-Infeasible Linear Programs from MIPLIB 2017},<br>
    &nbsp;&nbsp;howpublished = {\\url{$url}},<br>
    &nbsp;&nbsp;year&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {2026}<br>}""")

OVERVIEW = """
<div class="masthead">
  <span class="eyebrow">A benchmark of primal- and dual-infeasible linear programs</span>
  <h1>MIPLIB-Infeas</h1>
  <p class="sub">{n_samples} linear programs with no optimal solution, each
    derived from a <a href="https://miplib.zib.de/" target="_blank" rel="noopener">MIPLIB
    2017</a> instance with its integrality dropped. {n_primal}
    have no feasible point and the other
    {n_dual} are unbounded. They run up
    to {max_vars} variables and {max_cons}
    constraints.</p>
</div>
<div class="pair">{cards}</div>
<div class="section">
  <span class="eyebrow">Every instance</span>
  <h2>Two files</h2>
  <div class="files">
    <div class="file"><div class="fn">&lt;name&gt;.mps.gz</div>
      <p>The linear program, gzipped MPS, continuous variables only. Nothing to
      reconstruct before handing it to a solver.</p></div>
    <div class="file"><div class="fn">&lt;name&gt;.meta.json</div>
      <p>How that program was derived from its source instance: the branch the search
      took, or the bounds and constraints that were removed.</p></div>
  </div>
</div>
<div class="section">
  <span class="eyebrow">Citing</span>
  <h2>How to cite</h2>
  <div class="cite">{citation}</div>
  <p class="cite-note">Every instance
  derives from the MIPLIB 2017 collection, which should be cited alongside this one.</p>
</div>
<div class="section">
  <h2>Contact</h2>
  <div class="prose">
    <p class="muted">This collection is maintained by Haihao Lu and Bo Tang. If a
    published file does not have the status it claims, or a source instance carries terms
    other than the default, please
    <a href="https://github.com/MIT-Lu-Lab/MIPLIB-Infeas/issues">open an issue</a> and
    the affected file will be corrected or withdrawn.</p>
  </div>
</div>
"""


def _dataset_jsonld(totals: dict, site_url: str,
                    release_base_url: str | None) -> Markup:
    """A schema.org/Dataset description of the collection.

    Dataset search engines read this and nothing else on the page: without it the
    collection is a web page that happens to mention linear programs, and the
    people most likely to want it never find it.
    """
    n = totals["counts"]
    doc = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "MIPLIB-Infeas",
        "alternateName": ("Primal- and Dual-Infeasible Linear Programs "
                          "from MIPLIB 2017"),
        "description": (
            f"{totals['n_samples']} linear programs with no optimal solution, each "
            "derived from a MIPLIB 2017 instance with its integrality dropped. "
            f"{n.get('primal', 0)} have no feasible point, each the side of a branch "
            "a branch-and-bound search did not explore. The other "
            f"{n.get('dual', 0)} are feasible with an unbounded objective, produced "
            "by removing a minimal set of bounds and constraints from a root "
            f"relaxation. They run up to {totals['max_vars']} variables and "
            f"{totals['max_cons']} constraints."),
        "url": site_url,
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
        "keywords": ["linear programming", "infeasibility detection",
                     "unbounded linear programs", "benchmark", "MIPLIB",
                     "mathematical optimization"],
        "creator": [{"@type": "Person", "name": "Haihao Lu"},
                    {"@type": "Person", "name": "Bo Tang"}],
        "isBasedOn": "https://miplib.zib.de/",
        "encodingFormat": ["application/gzip", "application/json"],
    }
    if release_base_url:
        base = release_base_url.rstrip("/")
        doc["distribution"] = [
            {"@type": "DataDownload", "name": f"{info['label']} instances",
             "encodingFormat": "application/zip",
             "contentUrl": f"{base}/{info['slug']}.zip"}
            for info in SUBSET_META.values()
        ]
    # JSON inside <script> is not HTML: the one sequence that would end the
    # element early is escaped, and nothing else may be.
    payload = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return el("script", Markup(payload.replace("</", "<\\/")),
              type="application/ld+json")


def render_overview(totals: dict, site_url: str | None = None,
                    release_base_url: str | None = None) -> str:
    """The site root.

    Args:
        site_url (str | None): public URL of the published site, used in the
            citation block and in the machine-readable description. A
            placeholder stands in until it is known.
        release_base_url (str | None): the release prefix, which the
            machine-readable description points at for the archives.
    """
    site_url = site_url or "https://REPLACE-WITH-THE-PUBLISHED-SITE-URL"
    n = totals["counts"]
    cards = join(
        fmt(CARD, tone=info["tone"], slug=info["slug"], label=info["label"],
            count=fmt_int(n.get(key, 0)), blurb=SUBSET_BLURB[key])
        for key, info in SUBSET_META.items()
    )
    body = fmt(
        OVERVIEW,
        n_samples=fmt_int(totals["n_samples"]),
        n_primal=fmt_int(n.get("primal", 0)),
        n_dual=fmt_int(n.get("dual", 0)),
        max_vars=fmt_int(totals["max_vars"]),
        max_cons=fmt_int(totals["max_cons"]),
        cards=cards,
        citation=Markup(CITATION.substitute(url=esc(site_url))),
    )
    return page("MIPLIB-Infeas",
                join((_dataset_jsonld(totals, site_url, release_base_url), body)),
                active="overview", depth=0, narrow=True)
