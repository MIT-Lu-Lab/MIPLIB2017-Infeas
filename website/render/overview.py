"""The site root."""

from __future__ import annotations

from string import Template

from .. import content
from ..records import SUBSET_META, fmt_int
from ..urls import site_file
from .shell import Markup, el, esc, fmt, join, json_script, page

CARD = """<a class="subset {tone}" href="{slug}/">
      <h2>{label}</h2>
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
  <span class="eyebrow">{tagline}</span>
  <h1>{name}</h1>
  <p class="sub">{summary}</p>
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
      <p>How that program was derived from its source instance: the recorded branch
      for a primal-infeasible file; for a dual-infeasible file, either the bounds and
      constraints removed or that the source relaxation was already unbounded.</p></div>
  </div>
</div>
<div class="section">
  <span class="eyebrow">Citing</span>
  <h2>How to cite</h2>
  <div class="cite">{citation}</div>
  <p class="cite-note">Every instance derives from MIPLIB 2017. Please also cite
  <a href="https://doi.org/10.1007/s12532-020-00194-3">Gleixner et al.,
  “MIPLIB 2017: Data-Driven Compilation of the 6th Mixed-Integer Programming
  Library”</a>.</p>
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


def _dataset_jsonld(totals: dict, site_url: str | None,
                    release_base_url: str | None) -> Markup:
    """A schema.org/Dataset description of the collection.

    Dataset search engines read this and nothing else on the page: without it the
    collection is a web page that happens to mention linear programs, and the
    people most likely to want it never find it.
    """
    doc = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": content.NAME,
        "alternateName": ("Primal- and Dual-Infeasible Linear Programs "
                          "from MIPLIB 2017"),
        "description": content.collection_summary(totals),
        "keywords": ["linear programming", "infeasibility detection",
                     "unbounded linear programs", "benchmark", "MIPLIB",
                     "mathematical optimization"],
        "creator": [{"@type": "Person", "name": "Haihao Lu"},
                    {"@type": "Person", "name": "Bo Tang"}],
        "isBasedOn": "https://miplib.zib.de/",
        "encodingFormat": ["application/gzip", "application/json"],
    }
    if site_url:
        doc["url"] = site_url
        # Not "license": the source instances do not share one. 131 carry CC
        # BY-SA 4.0, one carries BSD 3-Clause and 130 carry none, so a single
        # machine-readable licence for the dataset would assert a grant nobody
        # ever made. usageInfo points a consumer at the notice that separates
        # the three, absolutely: this document is read off-site, where a
        # relative path resolves against nothing.
        doc["usageInfo"] = site_file(site_url, "LICENSE.txt")
    if release_base_url:
        base = release_base_url.rstrip("/")
        doc["distribution"] = [
            {"@type": "DataDownload", "name": f"{info['label']} instances",
             "encodingFormat": "application/zip",
             "contentUrl": f"{base}/{info['slug']}.zip"}
            for info in SUBSET_META.values()
        ]
    return json_script(doc, type="application/ld+json")


PAGE = "index.html"


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
    citation_url = site_url or content.PUBLIC_SITE_URL
    n = totals["counts"]
    cards = join(
        fmt(CARD, tone=info["tone"], slug=info["slug"], label=info["label"],
            count=fmt_int(n.get(key, 0)), blurb=content.SUBSET_CARD[key])
        for key, info in SUBSET_META.items()
    )
    summary = fmt(
        content.MASTHEAD_SUMMARY,
        n_samples=fmt_int(totals["n_samples"]),
        n_primal=fmt_int(n.get("primal", 0)),
        n_dual=fmt_int(n.get("dual", 0)),
        max_vars=fmt_int(totals["max_vars"]),
        max_cons=fmt_int(totals["max_cons"]),
        primal_verb="has" if n.get("primal", 0) == 1 else "have",
        dual_verb="is" if n.get("dual", 0) == 1 else "are",
        miplib=el("a", "MIPLIB 2017", href="https://miplib.zib.de/"),
    )
    body = fmt(
        OVERVIEW,
        tagline=content.TAGLINE,
        name=content.NAME,
        summary=summary,
        cards=cards,
        citation=Markup(CITATION.substitute(url=esc(citation_url))),
    )
    return page(content.NAME,
                join((_dataset_jsonld(totals, site_url, release_base_url), body)),
                active="overview", page_rel=PAGE, narrow=True,
                description=content.overview_description(totals),
                site_url=site_url)
