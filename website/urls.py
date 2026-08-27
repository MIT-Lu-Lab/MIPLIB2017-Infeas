"""Where a link points. One model, rather than one per call site.

A page-to-page link was built five different ways: the shell multiplied "../"
by a depth it was handed, an instance page wrote "../../" into its crosslink,
the download card wrote "../" into its index link, and two places each rstripped
a slash off the release prefix. The depth of a page was therefore stated twice,
once as a number and once as a count of dot-dots, with nothing keeping them in
step.

Here a page names its own path in the site and asks for a link to another one.
The same path also gives its canonical URL, so the two cannot disagree.
"""

from __future__ import annotations

import posixpath
from urllib.parse import urlsplit, urlunsplit

__all__ = ["normalize_site_url", "page_url", "rel", "site_file"]


def rel(from_page: str, to: str) -> str:
    """A relative URL from one generated page to another path in the site.

    Both are site-root-relative. `from_page` names the page's own file, so the
    link resolves against its directory. A `to` that names a directory keeps its
    trailing slash, which is what a page URL is; an empty one means the site
    root.

    Args:
        from_page (str): the linking page, e.g. "primal-infeasible/aaa/index.html".
        to (str): what to link to, e.g. "dual-infeasible/aaa/" or "assets/x.css".
    """
    out = posixpath.relpath(to or ".", posixpath.dirname(from_page) or ".")
    if out == ".":
        return "./"
    if (not to or to.endswith("/")) and not out.endswith("/"):
        out += "/"
    return out


def normalize_site_url(site_url: str | None) -> str | None:
    """Return an absolute public base URL with exactly one trailing slash."""
    if site_url is None:
        return None
    if (not site_url or "\\" in site_url
            or any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7f for c in site_url)):
        raise SystemExit(f"--site-url must be an absolute HTTP(S) URL, got {site_url!r}")
    try:
        parts = urlsplit(site_url)
        _ = parts.port  # force validation of a malformed port
        hostname = parts.hostname
    except ValueError as exc:
        raise SystemExit(f"--site-url is invalid: {exc}") from exc
    if (parts.scheme not in {"http", "https"} or not parts.netloc or not hostname
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment):
        raise SystemExit(
            f"--site-url must be an absolute HTTP(S) base URL without credentials, "
            f"a query, or a fragment; got {site_url!r}")
    path = parts.path.rstrip("/") + "/"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _origin(site_url: str) -> str:
    """The public base, with exactly one trailing slash.

    normalize_site_url guarantees that of what the CLI is given, but a renderer
    can be called with a base directly, and one that ends without a slash used
    to produce a URL with a path segment glued to the file after it.
    """
    return site_url.rstrip("/") + "/"


def page_url(site_url: str, page_rel: str) -> str:
    """Map a generated ``index.html`` path to its public trailing-slash URL."""
    suffix = "index.html"
    if not page_rel.endswith(suffix):
        raise ValueError(f"not an HTML page path: {page_rel!r}")
    return _origin(site_url) + page_rel[:-len(suffix)]


def site_file(site_url: str, path: str) -> str:
    """A file published at the site root, as an absolute URL."""
    return _origin(site_url) + path.lstrip("/")
