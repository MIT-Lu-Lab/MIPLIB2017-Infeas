"""The shared page shell: escaping, the top bar, and the document."""

from __future__ import annotations

import html

from ..assets import CSS_NAME, JS_NAME
from ..records import SUBSET_META


NAV = [
    ("overview", "", "Overview"),
    ("primal", "primal-infeasible/", "Primal-infeasible"),
    ("dual", "dual-infeasible/", "Dual-infeasible"),
    ("guide", "guide/", "Guide"),
    ("download", "download/", "Download"),
    ("about", "about/", "About"),
]


def esc(value: object) -> str:
    """Escape a value for HTML text and for any quoted attribute.

    The stdlib escaper also covers the apostrophe, which the renderers rely on
    nowhere today but would need the moment an attribute is single-quoted.
    """
    return html.escape(str(value))


def page(title: str, body: str, active: str, depth: int, narrow: bool = False) -> str:
    """Wrap body in the shared shell.

    Args:
        title (str): browser title, used verbatim.
        body (str): the page's main content.
        active (str): nav key to mark current.
        depth (int): directory levels below the site root.
        narrow (bool): render a narrower main column. Prose pages want a
            container the reading measure fills; the browse tables do not.
    """
    up = "../" * depth
    subset_class = active if active in SUBSET_META else ""
    nav = "".join(
        f'<a href="{up}{href}"'
        + (' aria-current="page"' if key == active else "")
        + f">{esc(label)}</a>"
        for key, href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}assets/{CSS_NAME}">
</head>
<body data-view="{subset_class}">
<div class="topbar">
  <div class="topbar-inner">
    <a class="wordmark" href="{up}">MIPLIB<span class="dash">-</span>Infeas</a>
    <nav class="top">{nav}</nav>
  </div>
  <div class="hairline"><span></span><span></span></div>
</div>
<main{' class="narrow"' if narrow else ''}>{body}</main>
<script src="{up}assets/{JS_NAME}" defer></script>
</body>
</html>
"""
