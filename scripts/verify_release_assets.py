"""Check the release still carries exactly what the site index promises.

    python scripts/verify_release_assets.py --repo MIT-Lu-Lab/MIPLIB2017-Infeas --tag v1.0

Every download link on the site is derived from one release prefix, so a renamed,
missing or re-uploaded asset turns into a dead link on a page that says nothing is
wrong. This compares the release's asset list against the index: the two files of
every instance, at the sizes the index records, plus the two archives and the two
CSV indexes.

Only the API's listing is fetched, not the 2.4 GB it describes. A size mismatch
means the asset was replaced; verifying the contents needs the files themselves
and is what scripts/verify_published.py is for.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from website.load import load_index

API = "https://api.github.com"


def fetch_assets(repo: str, tag: str, token: str | None) -> dict[str, int]:
    """name -> size for every asset on the release, following pagination."""
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def get(url):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=headers), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{url}: HTTP {e.code} {e.reason}") from e

    release = get(f"{API}/repos/{repo}/releases/tags/{tag}")
    assets, page = {}, 1
    while True:
        batch = get(f"{API}/repos/{repo}/releases/{release['id']}/assets"
                    f"?per_page=100&page={page}")
        if not batch:
            return assets
        for a in batch:
            assets[a["name"]] = a["size"]
        page += 1


def expected(samples) -> dict[str, int]:
    """name -> size for everything the site links to."""
    want = {}
    for s in samples:
        want[f"{s.stem}.mps.gz"] = s.file_bytes
        want[f"{s.stem}.meta.json"] = s.meta_bytes
    return want


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="OWNER/NAME")
    parser.add_argument("--tag", default="v1.0")
    parser.add_argument("--index", type=Path, default=root / "metadata" / "site-index.json")
    args = parser.parse_args()

    samples = load_index(args.index)
    want = expected(samples)
    # the browse and download pages link these by name, so they are part of the
    # contract even though no instance record mentions them. LICENSE.txt is here
    # for a different reason: an archive is what a reader takes away, and the
    # terms have to travel with it, so the notice is a release asset in its own
    # right and an unexpected-asset failure must not be what says so.
    archives = ["primal-infeasible.zip", "dual-infeasible.zip",
                "primal-infeasible.csv", "dual-infeasible.csv",
                "LICENSE.txt"]
    have = fetch_assets(args.repo, args.tag, os.environ.get("GITHUB_TOKEN"))
    print(f"index: {len(samples)} instances, {len(want)} files, "
          f"plus {len(archives)} archives and indexes")
    print(f"release {args.repo}@{args.tag}: {len(have)} assets")

    missing = sorted(n for n in want if n not in have)
    resized = sorted(n for n, size in want.items()
                     if n in have and have[n] != size)
    absent_archives = [n for n in archives if n not in have]
    extra = sorted(set(have) - set(want) - set(archives))

    for label, names in (("missing from the release", missing),
                         ("a different size than the index records", resized),
                         ("archives or indexes missing", absent_archives),
                         ("on the release but not in the index", extra)):
        if names:
            print(f"\n{len(names)} {label}:")
            for n in names[:20]:
                detail = (f"  index {want[n]} B, release {have[n]} B"
                          if n in resized else "")
                print(f"  {n}{detail}")
            if len(names) > 20:
                print(f"  ... and {len(names) - 20} more")

    bad = len(missing) + len(resized) + len(absent_archives) + len(extra)
    if bad:
        raise SystemExit(f"\n{bad} problem(s); every download link is derived from "
                         "this release, so each one is a dead link on a live page")
    print("\nevery file the site links to is on the release, at the recorded size")


if __name__ == "__main__":
    main()
