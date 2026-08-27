"""Cut the shipped faces down to the glyphs the site actually sets.

The complete IBM Plex faces are 490 KB, which is 93% of a first visit, and the
pages set 104 distinct characters. Subsetting removes four fifths of that.

Two things follow from the licence and are not optional. IBM Plex is under the
SIL Open Font License with the Reserved Font Name "Plex"; the OFL counts
deleting glyphs as a Modified Version, and clause 3 forbids a Modified Version
from using the Reserved Font Name. So the faces written here are renamed, and
the copyright and licence records travel with them unchanged. fonts/LICENSE.txt
stays beside them.

Run offline, against a checkout of the upstream release; the result is
committed. The build itself never runs this and takes no dependency on it.

    pip install fonttools brotli
    python scripts/subset_fonts.py --source-dir path/to/IBMPlex/woff2

Upstream: https://github.com/IBM/plex, OFL 1.1.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from website import assets, build_site

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "fonts"

# (upstream file stem, family, style)
FACES = (
    ("IBMPlexMono-Regular", "Mono", "Regular"),
    ("IBMPlexMono-Medium", "Mono", "Medium"),
    ("IBMPlexMono-SemiBold", "Mono", "SemiBold"),
    ("IBMPlexSans-Regular", "Sans", "Regular"),
    ("IBMPlexSans-Medium", "Sans", "Medium"),
    ("IBMPlexSans-SemiBold", "Sans", "SemiBold"),
    ("IBMPlexSerif-Regular", "Serif", "Regular"),
    ("IBMPlexSerif-SemiBold", "Serif", "SemiBold"),
)

# Kept beyond what the pages set today, so that one instance name with an
# accent, or one more piece of punctuation in the prose, is a page edit rather
# than a re-subset and a new set of binaries.
MARGIN = "".join(chr(code) for code in (
    *range(0x00C0, 0x0100),                    # the Latin-1 accented letters
    0x00A0, 0x00AD,                            # no-break space, soft hyphen
    0x00A9, 0x00AE, 0x00B0, 0x00B1, 0x00B7,    # (c) (r) degree plus-minus middot
    0x00AB, 0x00BB, 0x2039, 0x203A,            # the angle quotation marks
    0x2018, 0x201A, 0x201E,                    # the quotation marks not yet set
    0x2020, 0x2021, 0x2022, 0x2030, 0x2044,    # dagger ddagger bullet permille slash
    0x20AC, 0x2122,                            # euro, trademark
    0x2191, 0x2205, 0x221E, 0x2248, 0x2260,    # up-arrow empty-set infinity approx ne
    0x27E8, 0x27E9,                            # the mathematical angle brackets
))

# The name records a subset keeps: the copyright, which the OFL requires to
# travel, and the version. Every other record from the source, including the
# trademark and the unique identifier, names the original and is dropped rather
# than carried onto something else.
_KEEP_FROM_SOURCE = (0, 5)

# The upstream web faces carry no licence record, so the subset states it. The
# full text stays beside the files, in fonts/LICENSE.txt.
_LICENSE = ("This Font Software is licensed under the SIL Open Font License, "
            "Version 1.1. This license is available with a FAQ at: "
            "https://scripts.sil.org/OFL")
_LICENSE_URL = "https://scripts.sil.org/OFL"
_WINDOWS_EN = (3, 1, 0x409)
_MAC_EN = (1, 0, 0)


def rendered_characters(site_dir: Path) -> set[str]:
    """Every printable character the built pages set.

    Read from the pages rather than listed by hand: a glyph that is missing
    falls back to whatever the reader happens to have installed, which is the
    kind of thing nobody notices until it is on a projector.
    """
    found: set[str] = set()
    for page in site_dir.rglob("*.html"):
        text = re.sub(r"<(script|style)\b.*?</\1>", " ",
                      page.read_text(encoding="utf-8"), flags=re.S)
        found |= set(html.unescape(re.sub(r"<[^>]+>", " ", text)))
    for sheet in (site_dir / "assets").glob("*.css"):
        for match in re.finditer(r'content:\s*"([^"]*)"', sheet.read_text(encoding="utf-8")):
            found |= set(match.group(1))
    return {c for c in found if c.isprintable() and not c.isspace()}


def build_variants(into: Path) -> list[Path]:
    """Both builds the pages have branches for.

    A published build renders the download links and the arrow in them; a build
    without a release URL renders the disabled placeholders instead. Neither one
    alone sets every character the site can, which is how the arrow in the
    archive link came to be dropped from a subset taken from one of them.
    """
    published = into / "published"
    build_site.build(build_site.DEFAULT_INDEX, published,
                     release_base_url="https://example.invalid/dl",
                     site_url="https://example.invalid/",
                     miplib_path=build_site.DEFAULT_MIPLIB)
    placeholders = into / "placeholders"
    build_site.build(build_site.DEFAULT_INDEX, placeholders,
                     miplib_path=build_site.DEFAULT_MIPLIB)
    return [published, placeholders]


def charset(site_dirs: list[Path]) -> str:
    found = set(MARGIN)
    for site_dir in site_dirs:
        found |= rendered_characters(site_dir)
    return "".join(sorted(found))


def _rename(font, family: str, style: str) -> None:
    from fontTools.ttLib.tables._n_a_m_e import NameRecord

    full = family if style == "Regular" else f"{family} {style}"
    postscript = f"{family.replace(' ', '')}-{style}"
    table = font["name"]
    kept: list[NameRecord] = [r for r in table.names if r.nameID in _KEEP_FROM_SOURCE]
    table.names = kept
    for name_id, value in ((1, family), (2, style), (3, f"{postscript}; subset"),
                           (4, full), (6, postscript), (13, _LICENSE),
                           (14, _LICENSE_URL), (16, family), (17, style)):
        for platform, encoding, language in (_WINDOWS_EN, _MAC_EN):
            table.setName(value, name_id, platform, encoding, language)


def subset_face(source: Path, dest: Path, family: str, style: str, text: str) -> None:
    from fontTools import subset

    options = subset.Options(flavor="woff2", layout_features=["kern", "liga"])
    font = subset.load_font(str(source), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    _rename(font, family, style)
    subset.save_font(font, str(dest), options)
    font.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, required=True,
                        help="a checkout of the upstream IBM Plex woff2 files")
    parser.add_argument("--out-dir", type=Path, default=FONT_DIR)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        text = charset(build_variants(Path(tmp)))

    print(f"{len(text)} glyphs kept\n")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    before = after = 0
    for stem, family, style in FACES:
        source = args.source_dir / f"{stem}.woff2"
        if not source.is_file():
            raise SystemExit(f"{source}: not found. --source-dir should hold the "
                             "upstream woff2 files.")
        dest = args.out_dir / assets.font_file(family, style)
        subset_face(source, dest, f"{assets.FONT_FAMILY} {family}", style, text)
        before += source.stat().st_size
        after += dest.stat().st_size
        print(f"  {dest.stat().st_size:>7,}  was {source.stat().st_size:>7,}  {dest.name}")
    print(f"\n  {after:>7,}  was {before:>7,}  ({1 - after / before:.0%} smaller)")


if __name__ == "__main__":
    main()
