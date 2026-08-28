"""A query over rendered HTML, so a test can say what it means.

Assertions used to match the markup as text: `'<details class="facets" open>'
in html`. That passes only for one spelling of one attribute order, says
nothing about what is being checked, and turns a class rename into a dozen red
tests that were not about the class.

Here a test says `page(html).one("details.facets").has("open")`. The parsing is
BeautifulSoup's, and so are the selectors, which are ordinary CSS. What is
written here is the part no library does: `one` insists there is exactly one
match, which is usually the real claim a test is making, and says which way it
failed when there is not.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

__all__ = ["Element", "page"]


class Element:
    """One parsed element, asked about the way a test wants to ask."""

    def __init__(self, tag: Tag) -> None:
        self.tag = tag

    @property
    def classes(self) -> set[str]:
        value = self.tag.get("class") or []
        return set(value if isinstance(value, list) else str(value).split())

    def has(self, name: str) -> bool:
        """Whether the attribute is present, with or without a value."""
        return name in self.tag.attrs

    def get(self, name: str) -> str | None:
        value = self.tag.get(name)
        return " ".join(value) if isinstance(value, list) else value

    @property
    def text(self) -> str:
        """The element's text and its descendants', whitespace normalised."""
        return " ".join(self.tag.get_text(" ").split())

    @property
    def children(self) -> list[Element]:
        """The child elements, without the text between them."""
        return [Element(child) for child in self.tag.find_all(recursive=False)]

    def all(self, selector: str) -> list[Element]:
        """Every descendant the CSS selector matches."""
        return [Element(found) for found in self.tag.select(selector)]

    def one(self, selector: str) -> Element:
        """The only descendant matching, or a failure naming what went wrong."""
        found = self.tag.select(selector)
        assert found, f"nothing matches {selector!r}"
        assert len(found) == 1, f"{len(found)} elements match {selector!r}"
        return Element(found[0])

    def first(self, selector: str) -> Element:
        found = self.tag.select(selector)
        assert found, f"nothing matches {selector!r}"
        return Element(found[0])


def page(html: str) -> Element:
    """Parse a rendered page into something a test can ask questions of."""
    return Element(BeautifulSoup(html, "html.parser"))
