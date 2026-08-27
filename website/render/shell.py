"""The shared page shell: the top bar and the document around a page body."""

from __future__ import annotations

from ..assets import CSS_NAME, JS_NAME
from ..records import SUBSET_META
from .markup import Markup, el, esc, fmt, join

__all__ = ["NAV", "Markup", "el", "esc", "fmt", "join", "page"]


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
<link rel="stylesheet" href="{up}assets/{css}">
</head>
<body data-view="{view}">
<div class="topbar">
  <div class="topbar-inner">
    <a class="wordmark" href="{up}">MIPLIB<span class="dash">-</span>Infeas</a>
    <nav class="top" aria-label="Primary navigation">{nav}</nav>
  </div>
  <div class="hairline"><span></span><span></span></div>
</div>
{main}
<script src="{up}assets/{js}" defer></script>
</body>
</html>
"""


def _nav_label(label: str, short: str) -> Markup:
    """A nav label, carrying a short form when the name has one."""
    if not short:
        return esc(label)
    return join((el("span", label, class_="nav-full"),
                 el("span", short, class_="nav-short")))


def page(title: str, body: Markup, active: str, depth: int,
         narrow: bool = False) -> str:
    """Wrap a page body in the shared document.

    Args:
        title (str): browser title.
        body (Markup): the page's content, already rendered.
        active (str): nav key to mark current.
        depth (int): directory levels below the site root.
        narrow (bool): render a narrower main column. Prose pages want a
            container the reading measure fills; the browse tables do not.
    """
    up = "../" * depth
    nav = join(
        el("a", _nav_label(label, short), href=f"{up}{href}",
           aria_current="page" if key == active else None)
        for key, href, label, short in NAV
    )
    return fmt(
        DOCUMENT,
        title=title,
        up=up,
        css=CSS_NAME,
        js=JS_NAME,
        view=active if active in SUBSET_META else "",
        nav=nav,
        main=el("main", body, class_="narrow" if narrow else None),
    )
