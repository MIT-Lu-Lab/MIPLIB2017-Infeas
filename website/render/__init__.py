"""HTML rendering. Each module owns one page type; shell owns the document."""

from .browse import page_rel as browse_page_rel, render_browse
from .instance import render_sample
from .overview import render_overview
from .shell import Markup, esc, page
from .static import render_about, render_download, render_guide

__all__ = [
    "Markup", "browse_page_rel", "esc", "page",
    "render_about", "render_browse", "render_download", "render_guide",
    "render_overview", "render_sample",
]
