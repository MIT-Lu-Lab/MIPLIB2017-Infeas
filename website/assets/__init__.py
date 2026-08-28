"""Compile the colocated stylesheet and script into fingerprinted assets."""

import hashlib
from pathlib import Path

# Self-hosted IBM Plex subsets. The modified family name is required by the
# OFL's Reserved Font Name rule.
FONT_FAMILY = "Infeas"

# The card a shared link shows, drawn by scripts/make_og_image.py and published
# at the site root. Its size is what the platforms crop to, and is declared in
# the head so they need not fetch it to lay out the card.
OG_IMAGE = "og.png"
OG_IMAGE_SIZE = (1200, 630)

FONT_FACES = (
    ("Mono", "Regular", 400),
    ("Mono", "Medium", 500),
    ("Mono", "SemiBold", 600),
    ("Sans", "Regular", 400),
    ("Sans", "Medium", 500),
    ("Sans", "SemiBold", 600),
    ("Serif", "Regular", 400),
    ("Serif", "SemiBold", 600),
)


def font_file(family: str, style: str) -> str:
    """The shipped file for one face, relative to fonts/."""
    return f"{FONT_FAMILY}{family}-{style}.woff2"


def _font_faces():
    """The @font-face rules, resolved from the stylesheet in ``assets/``."""
    return "".join(
        f"@font-face{{font-family:'{FONT_FAMILY} {family}';font-style:normal;"
        f"font-weight:{weight};font-display:swap;"
        f"src:url(../fonts/{font_file(family, style)}) format('woff2')}}"
        for family, style, weight in FONT_FACES
    )


_ASSET_DIR = Path(__file__).parent
_COMPACT_TOKEN = "COMPACT_PX"


def _read_asset(name: str) -> str:
    return (_ASSET_DIR / name).read_text(encoding="utf-8")


# The one width at which the layout stops being a desktop layout. Both the
# stylesheet and the script have to know it and neither can read the other's
# copy, so each writes COMPACT_PX and it is filled in once, here.
COMPACT_WIDTH = 780


def _fill(text: str) -> str:
    count = text.count(_COMPACT_TOKEN)
    if count != 1:
        raise RuntimeError(f"asset must contain exactly one {_COMPACT_TOKEN!r}; found {count}")
    return text.replace(_COMPACT_TOKEN, f"{COMPACT_WIDTH}px")


SITE_CSS = _fill(_font_faces() + _read_asset("site.css"))
SITE_JS = _fill(_read_asset("browse.js"))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


CSS_NAME = f"site.{_digest(SITE_CSS)}.css"
JS_NAME = f"site.{_digest(SITE_JS)}.js"
