"""One way to write an SVG element, so no drawing has to remember escaping.

Every attribute goes through ``quoteattr`` and every piece of text through
``escape``, because they go through this and nothing else. Numbers are rounded
here too: the drawings are a thousand user units across and render around five
hundred pixels wide, so a decimal is half a pixel nobody sees and two bytes on
every dot of every page.
"""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

# Attribute names that are Python keywords or hyphenated take a trailing
# underscore or an inner one: class_ -> class, text_anchor -> text-anchor.
Value = str | float | int | None


def num(value: float) -> str:
    """A coordinate at the precision a screen can show, and no more."""

    return str(round(value))


def _attr(value: Value) -> str:
    return quoteattr(num(value) if isinstance(value, float) else str(value))


def el(name: str, text: str | None = None, **attrs: Value) -> str:
    """One element, self-closing unless it is given text.

    ``text`` is escaped. Pass markup already built by this module as a child
    through ``group`` instead, which does not escape what it is handed.
    """

    written = "".join(
        f" {key.rstrip('_').replace('_', '-')}={_attr(value)}"
        for key, value in attrs.items()
        if value is not None
    )
    if text is None:
        return f"<{name}{written}/>"
    return f"<{name}{written}>{escape(text)}</{name}>"


def group(name: str, children: str, **attrs: Value) -> str:
    """One element wrapping markup this module already built."""

    written = "".join(
        f" {key.rstrip('_').replace('_', '-')}={_attr(value)}"
        for key, value in attrs.items()
        if value is not None
    )
    return f"<{name}{written}>{children}</{name}>"


def svg(children: str, width: float, height: float, **attrs: Value) -> str:
    """A drawing, sized in user units and scaled by the stylesheet."""

    return group(
        "svg",
        children,
        viewBox=f"0 0 {num(width)} {num(height)}",
        xmlns="http://www.w3.org/2000/svg",
        **attrs,
    )


def power_of_ten(exponent: int, dy: float = -14) -> str:
    """A tick label, with the exponent raised rather than written 10^5."""

    return f"10{el('tspan', str(exponent), class_='exp', dy=dy)}"
