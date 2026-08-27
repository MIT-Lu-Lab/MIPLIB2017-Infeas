"""The shipped faces are subsets, so what they leave out is now a question.

A glyph the files do not carry falls back to whatever the reader happens to
have installed, which nobody notices until it is on a projector. These read the
actual files rather than a manifest of what the subsetter meant to keep.
"""

import re
import sys
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from website import assets as A

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"
sys.path.insert(0, str(ROOT / "scripts"))

import subset_fonts  # noqa: E402

INDEX = ROOT / "metadata" / "site-index.json"
pytestmark = pytest.mark.skipif(not INDEX.is_file(), reason="site index not present")


@pytest.fixture(scope="module")
def needed(tmp_path_factory) -> set[str]:
    """Every character the pages set, over both builds they have branches for."""
    sites = subset_fonts.build_variants(tmp_path_factory.mktemp("charset"))
    found: set[str] = set()
    for site in sites:
        found |= subset_fonts.rendered_characters(site)
    return found


def _shipped():
    for family, style, _ in A.FONT_FACES:
        yield FONTS / A.font_file(family, style)


def test_the_stylesheet_asks_for_the_files_that_ship():
    asked = set(re.findall(r"url\(fonts/([^)]+)\)", A.font_face()))
    shipped = {path.name for path in FONTS.glob("*.woff2")}
    assert asked == shipped


def test_every_character_the_pages_set_is_in_every_face(needed):
    """Every face, not just one: a heading is serif and a bound is mono, and a
    character can reach either."""
    assert len(needed) > 50, "the character set looks unread"
    for path in _shipped():
        cmap = set(TTFont(path).getBestCmap())
        missing = sorted(c for c in needed if ord(c) not in cmap)
        assert not missing, f"{path.name} is missing {missing}"


def test_the_subsets_do_not_use_the_reserved_font_name():
    """IBM Plex is under the OFL with the Reserved Font Name "Plex". Removing
    glyphs makes a Modified Version, and clause 3 forbids one from using that
    name, so these are published as another family."""
    for path in _shipped():
        names = " ".join(str(record) for record in TTFont(path)["name"].names)
        assert "Plex" not in names, path.name
        assert A.FONT_FAMILY in names, path.name


def test_the_subsets_carry_the_notice_the_licence_requires():
    for path in _shipped():
        names = " ".join(str(record) for record in TTFont(path)["name"].names)
        assert "IBM Corp" in names, f"{path.name}: no copyright"
        assert "Open Font License" in names, f"{path.name}: no licence"
    assert (FONTS / "LICENSE.txt").is_file()


def test_a_subset_is_worth_taking():
    """The complete faces were 490 KB and 93% of a first visit. If a future
    subset stops being much smaller than that, it is not doing its job."""
    total = sum(path.stat().st_size for path in _shipped())
    assert total < 150_000, f"{total:,} bytes of fonts"
