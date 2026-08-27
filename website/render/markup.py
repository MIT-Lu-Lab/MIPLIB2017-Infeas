"""The one rule the renderers share: text is escaped, HTML is declared.

Before this module every helper carried its own convention about which of its
arguments were already markup and which were text, and no two agreed: `_kv`
escaped the key and not the value, `_panel` the title and not the body, the
facet rail the group label and not the option. Nothing enforced any of them, and
two were wrong, which is also how HTML entities ended up inside the label data
(`"50 K &ndash; 500 K"`) to survive an interpolation that would not escape them.

Here a value is text unless it says otherwise by being `Markup`. Everything that
reaches the page goes through `esc`, so a raw interpolation is not something a
renderer can do by accident.
"""

from __future__ import annotations

import html
import json

__all__ = ["Markup", "attr", "el", "esc", "fmt", "join", "json_script"]

# Elements with no closing tag. The generator emits no others.
_VOID = frozenset({"br", "hr", "img", "input", "link", "meta"})


class Markup(str):
    """A string that is already HTML.

    Wrapping a literal is a claim about it: that its author checked the markup.
    Everything not wrapped is text, and `esc` escapes it.
    """

    __slots__ = ()

    def __html__(self) -> str:
        return str(self)


def esc(value: object) -> Markup:
    """Escape a value for HTML text. `Markup` passes through unchanged.

    The stdlib escaper also covers the apostrophe, which matters the moment an
    attribute is single-quoted.
    """
    if isinstance(value, Markup):
        return value
    return Markup(html.escape(str(value)))


def attr(value: object) -> str:
    """Escape a value for a quoted attribute.

    Unlike `esc` this does not honour `Markup`: an attribute value is never
    markup, so a fragment that reached one would be a mistake to preserve.
    """
    return html.escape(str(value))


def join(parts) -> Markup:
    """Concatenate fragments, escaping any that are not already `Markup`."""
    return Markup("".join(esc(p) for p in parts))


def el(tag: str, *children: object, **attrs: object) -> Markup:
    """One element, with its children and attribute values escaped.

    An attribute is omitted when its value is None or False and rendered bare
    when it is True. A trailing underscore is dropped and the remaining ones
    become dashes, so `class_` and `data_k` reach the page as `class` and
    `data-k`.
    """
    parts = [f"<{tag}"]
    for name, value in attrs.items():
        if value is None or value is False:
            continue
        key = name.rstrip("_").replace("_", "-")
        parts.append(f" {key}" if value is True else f' {key}="{attr(value)}"')
    parts.append(">")
    if tag not in _VOID:
        parts.extend(esc(c) for c in children)
        parts.append(f"</{tag}>")
    return Markup("".join(parts))


def fmt(template: str, /, **values: object) -> Markup:
    """Fill a markup template, escaping every substitution.

    The template is the shape of the page and is `Markup` by construction; the
    values are text unless they say otherwise. `str.format_map` rather than an
    f-string, because an f-string interpolates whatever it is handed and there
    is no way to make that fail.
    """
    return Markup(template.format_map({k: esc(v) for k, v in values.items()}))


def json_script(payload: object, **attrs: object) -> Markup:
    """A JSON payload in a <script>, for the page to read back.

    Script content is not HTML and must not be escaped as if it were; the one
    sequence that would end the element early is, and nothing else is touched.
    """
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return el("script", Markup(text.replace("</", r"<\/")), **attrs)
