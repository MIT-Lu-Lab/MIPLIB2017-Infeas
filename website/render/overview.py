"""The site root."""

from __future__ import annotations

import json

from ..records import SUBSET_META, fmt_int
from .shell import page


def _dataset_jsonld(totals: dict, site_url: str, release_base_url: str | None) -> str:
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
    return ('<script type="application/ld+json">'
            + json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


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
    cards = "".join(
        f'''<a class="subset {SUBSET_META[key]['tone']}" href="{SUBSET_META[key]['slug']}/">
      <h3>{SUBSET_META[key]['label']}</h3>
      <div class="count">{fmt_int(n.get(key, 0))} instances</div>
      <p>{blurb}</p>
      <span class="go">Browse them all &rarr;</span>
    </a>'''
        for key, blurb in (
            ("primal",
             "A branch-and-bound run splits on a variable and explores one side of the "
             "split. This set collects the other side, at nodes where that side has no "
             "feasible point."),
            ("dual",
             "Bounds and constraints are removed from a MIPLIB relaxation until the "
             "objective becomes unbounded, then every removal that proves unnecessary is "
             "restored."),
        )
    )
    body = f"""
<div class="masthead">
  <span class="eyebrow">A large-scale detection benchmark</span>
  <h1>Primal- and dual-infeasible linear programs</h1>
  <p class="sub">{fmt_int(totals['n_samples'])} linear programs with no optimal solution, each
    derived from a <a href="https://miplib.zib.de/" target="_blank" rel="noopener">MIPLIB
    2017</a> instance with its integrality dropped. {fmt_int(n.get('primal', 0))}
    have no feasible point and the other
    {fmt_int(n.get('dual', 0))} are unbounded. They run up
    to {fmt_int(totals['max_vars'])} variables and {fmt_int(totals['max_cons'])}
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
  <div class="cite">@misc{{miplib_infeas,<br>
    &nbsp;&nbsp;author&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {{Haihao Lu and Bo Tang}},<br>
    &nbsp;&nbsp;title&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {{MIPLIB-Infeas: Primal- and Dual-Infeasible Linear Programs from MIPLIB 2017}},<br>
    &nbsp;&nbsp;howpublished = {{\\url{{{site_url}}}}},<br>
    &nbsp;&nbsp;year&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {{2026}}<br>}}</div>
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
    body = _dataset_jsonld(totals, site_url, release_base_url) + body
    return page("MIPLIB-Infeas", body, active="overview", depth=0, narrow=True)

