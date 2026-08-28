"""Normalize public bases and derive links from generated site paths."""

from __future__ import annotations

import posixpath
from urllib.parse import urlsplit, urlunsplit


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


def _normalize_http_base(value: str | None, *, label: str, trailing_slash: bool) -> str | None:
    if value is None:
        return None
    if (
        not value
        or "\\" in value
        or any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in value)
    ):
        raise ValueError(f"{label} must be an absolute HTTP(S) URL, got {value!r}")
    try:
        parts = urlsplit(value)
        _ = parts.port  # force validation of a malformed port
        hostname = parts.hostname
    except ValueError as exc:
        raise ValueError(f"{label} is invalid: {exc}") from exc
    if (
        parts.scheme not in {"http", "https"}
        or not parts.netloc
        or not hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise ValueError(
            f"{label} must be an absolute HTTP(S) base URL without credentials, "
            f"a query, or a fragment; got {value!r}"
        )
    path = parts.path.rstrip("/") + ("/" if trailing_slash else "")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def normalize_site_url(site_url: str | None) -> str | None:
    """Return an absolute public base URL with exactly one trailing slash."""
    return _normalize_http_base(site_url, label="site URL", trailing_slash=True)


def normalize_release_base_url(value: str | None) -> str | None:
    """Return a clean HTTP(S) release prefix without a trailing slash."""
    return _normalize_http_base(value, label="release base URL", trailing_slash=False)


def page_url(site_url: str, page_rel: str) -> str:
    """Map a generated ``index.html`` path to its public trailing-slash URL."""
    suffix = "index.html"
    if not page_rel.endswith(suffix):
        raise ValueError(f"not an HTML page path: {page_rel!r}")
    return site_url + page_rel[: -len(suffix)]


def site_file(site_url: str, path: str) -> str:
    """A file published at the site root, as an absolute URL."""
    return site_url + path.lstrip("/")
