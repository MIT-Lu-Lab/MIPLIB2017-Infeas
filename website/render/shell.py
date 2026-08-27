"""The shared page shell: the top bar and the document around a page body."""

from __future__ import annotations

from ..assets import CSS_NAME, JS_NAME
from ..content import NAME
from ..records import SUBSET_META
from ..urls import page_url, rel
from .markup import Markup, el, esc, fmt, join, json_script

__all__ = ["NAV", "Markup", "el", "esc", "fmt", "join", "json_script", "page"]


# (key, href, label, short label). A short label is given only where the full one
# does not fit a phone: six equal cells across 360px leave about 108px each, and
# "Primal-infeasible" wants more than that. Both ship; the stylesheet picks one.
NAV = [
    ("overview", "", "Overview", ""),
    ("primal", "primal-infeasible/", "Primal-infeasible", "Primal"),
    ("dual", "dual-infeasible/", "Dual-infeasible", "Dual"),
    ("guide", "guide/", "Guide", ""),
    ("download", "download/", "Download", ""),
    ("about", "about/", "About", ""),
]

DOCUMENT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
{head}
<link rel="stylesheet" href="{css_href}">
</head>
<body data-view="{view}">
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="topbar">
  <div class="topbar-inner">
    <a class="wordmark" href="{root}">MIPLIB<span class="dash">-</span>Infeas</a>
    <nav class="top" aria-label="Primary navigation">{nav}</nav>
  </div>
  <div class="hairline"><span></span><span></span></div>
</header>
{main}
<script src="{js_src}" defer></script>
</body>
</html>
"""


def _head_meta(title: str, description: str, canonical: str | None) -> Markup:
    """What a search result and a shared link show.

    Without these a page is a bare URL in a chat window and an untitled row in a
    result list, which for a collection meant to be cited is most of what a
    reader sees before deciding whether to open it.
    """
    tags = [el("meta", name="description", content=description),
            el("meta", property="og:type", content="website"),
            el("meta", property="og:site_name", content=NAME),
            el("meta", property="og:title", content=title),
            el("meta", property="og:description", content=description),
            el("meta", name="twitter:card", content="summary")]
    if canonical:
        # only the build knows the public origin, so a build without --site-url
        # says nothing rather than pointing at a guess
        tags.insert(1, el("link", rel="canonical", href=canonical))
        tags.insert(5, el("meta", property="og:url", content=canonical))
    return Markup(chr(10).join(tags))


def _nav_label(label: str, short: str) -> Markup:
    """A nav label, carrying a short form when the name has one."""
    if not short:
        return esc(label)
    return join((el("span", label, class_="nav-full"),
                 el("span", short, class_="nav-short")))


def page(title: str, body: Markup, active: str, page_rel: str,
         narrow: bool = False, *, description: str = "",
         site_url: str | None = None) -> str:
    """Wrap a page body in the shared document.

    Args:
        title (str): browser title.
        body (Markup): the page's content, already rendered.
        active (str): nav key to mark current.
        page_rel (str): this page's path in the site, e.g. "guide/index.html".
            Every link on it and its canonical URL are derived from this, so
            the two cannot disagree about where the page sits.
        narrow (bool): render a narrower main column. Prose pages want a
            container the reading measure fills; the browse tables do not.
        description (str): what this page is, for a search result and a
            shared link. From website.content, never written here.
        site_url (str | None): the site's public origin, when the build was
            told it. Without one the page carries no canonical URL rather
            than a guessed one.
    """
    nav = join(
        el("a", _nav_label(label, short), href=rel(page_rel, href),
           aria_current="page" if key == active else None,
           aria_label=label if short else None)
        for key, href, label, short in NAV
    )
    canonical = page_url(site_url, page_rel) if site_url else None
    return fmt(
        DOCUMENT,
        title=title,
        head=_head_meta(title, description, canonical),
        root=rel(page_rel, ""),
        css_href=rel(page_rel, f"assets/{CSS_NAME}"),
        js_src=rel(page_rel, f"assets/{JS_NAME}"),
        view=active if active in SUBSET_META else "",
        nav=nav,
        main=el("main", body, id="main-content", tabindex="-1",
                class_="narrow" if narrow else None),
    )
