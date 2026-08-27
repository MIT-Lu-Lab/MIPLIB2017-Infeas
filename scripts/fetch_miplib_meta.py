"""Fetch per-instance metadata from MIPLIB 2017 and cache it for the site build.

    python scripts/fetch_miplib_meta.py [--out metadata/miplib_meta.json]

CC BY-SA 4.0 requires that adapted material identify the creator of the original.
This collection derives every instance from MIPLIB 2017 but named no submitter
anywhere, so the attribution obligation was not being met. This script collects
the submitter along with the tags, group and description MIPLIB publishes, so the
sample pages can credit the source and describe what the original models.

One request per source instance, rate limited, run once and the result committed.
The site build never touches the network: it reads only the cached JSON, and
renders without any of these fields when the cache is absent.
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "https://miplib.zib.de/instance_details_{name}.html"
UA = "miplib2017-infeas-metadata/1.0 (one-off attribution fetch)"



def fetch(name, timeout=30):
    """Fetch one instance page, or None if MIPLIB has no page for it."""
    req = urllib.request.Request(BASE.format(name=name), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse(page):
    """Pull submitter, tags, group, status and description out of one page."""
    out = {}

    # the summary table's header row names the columns; the next row holds them
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)
    for i, row in enumerate(rows):
        cells = [_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
        if "Submitter" in cells and i + 1 < len(rows):
            values = [_text(c) for c in
                      re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[i + 1], re.S)]
            for key, val in zip(cells, values, strict=False):
                key = key.strip().lower()
                # an en dash, not a hyphen: it is what MIPLIB puts in an empty cell
                if key in ("submitter", "status", "group") and val and val != "–":
                    out[key] = val
            break

    # description is the first paragraph, before the boilerplate sections
    for para in re.findall(r"<p[^>]*>(.*?)</p>", page, re.S):
        t = _text(para)
        if not t or t.startswith(("Location of instance", "Detailed explanation",
                                  "Available nonzero", "Nonzero entries",
                                  "The following instances")):
            continue
        # MIPLIB appends its own provenance note to many descriptions. It says
        # nothing about the model and runs into the preceding sentence without
        # punctuation, so it is lifted out of the description rather than shown
        # with it. It is kept, not dropped: this note is MIPLIB's own statement
        # of which edition an instance came from, and it is the only per-instance
        # evidence of that. An instance it names as imported predates MIPLIB
        # 2017's submission form, and so predates the licence that form required,
        # which is what LICENSE turns on.
        # It is not always last. MIPLIB puts it at the front of some entries and
        # in the middle of others, so this cannot be anchored to the end.
        m = re.search(r"Imported from (?:the )?MIPLIB\s*\d*(?: submissions)?\.",
                      t, flags=re.I)
        if m:
            out["imported_from"] = m.group(0).strip()
            t = " ".join((t[: m.start()] + " " + t[m.end():]).split())
        if t:
            out["description"] = t
        break

    # the instance's own tags sit in the <h3> right after the <h1> title. Other
    # tag_*.html links on the page belong to the "similar instances" table and
    # describe different instances entirely.
    m = re.search(r"<h1>.*?</h1>\s*<h3>(.*?)</h3>", page, re.S)
    if m:
        tags = sorted(set(re.findall(r'href="tag_([a-z_0-9]+)\.html"', m.group(1))))
        tags = [t for t in tags if t not in ("easy", "hard", "open")]
        if tags:
            out["tags"] = tags
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "dataset")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parents[1]
                        / "metadata" / "miplib_meta.json")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="seconds between requests; this is someone else's server")
    args = parser.parse_args()

    names = set()
    for sub, suffix in (("infeasible", "_if"), ("unbounded", "_ub")):
        d = args.dataset_dir / sub
        if d.is_dir():
            names |= {p.name[: -len(f"{suffix}.mps.gz")]
                      for p in d.glob(f"*{suffix}.mps.gz")}
    names = sorted(names)
    print(f"fetching metadata for {len(names)} source instances", flush=True)

    cache = {}
    if args.out.exists():                       # resume a partial run
        cache = json.loads(args.out.read_text(encoding="utf-8"))
        print(f"  {len(cache)} already cached", flush=True)

    missing = []
    for n, name in enumerate(names, 1):
        if name in cache:
            continue
        page = fetch(name)
        if page is None:
            missing.append(name)
        else:
            cache[name] = parse(page)
        if n % 20 == 0 or n == len(names):
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  {n}/{len(names)}", flush=True)
        time.sleep(args.delay)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")

    def have(k):
        return sum(1 for v in cache.values() if v.get(k))

    print(f"\nwrote {args.out}  ({len(cache)} instances)")
    print(f"  submitter: {have('submitter')}   tags: {have('tags')}   "
          f"description: {have('description')}   group: {have('group')}")
    if missing:
        print(f"  no MIPLIB page for {len(missing)}: {', '.join(missing[:5])}")


if __name__ == "__main__":
    main()
