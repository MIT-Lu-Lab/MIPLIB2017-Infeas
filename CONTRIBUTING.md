# Working on this repository

This repository holds the generator for <https://mit-lu-lab.github.io/MIPLIB-Infeas>
and the metadata it renders. It does not hold the published linear programs: those
are 2.3 GB, four of them over GitHub's 100 MiB file limit, and they live on the
[release](https://github.com/MIT-Lu-Lab/MIPLIB-Infeas/releases).

## What is the source of truth

```
the published files on the release          the collection itself
  -> metadata/site-index.json               what the pages render, 0.2% of the sidecars
  -> the built site                          deployed by CI, never committed
```

Read that top to bottom. The instance pages, the browse tables and the two CSV
indexes are all derived from the index; the index is derived from the sidecars.
Nothing downstream is edited by hand, and nothing generated is committed.

`metadata/miplib_meta.json` comes in from the side: it is MIPLIB 2017's own
submitter, tags and description for each *source* instance, scraped once. It is
kept apart from the index so that re-fetching it does not need the published files
and rebuilding the index does not need the network.

## Building

Python 3.10 or later. The generator is standard library only, on purpose: the site
has to be buildable from a bare checkout years from now.

```bash
python -m website.build_site --out-dir _site \
  --release-base-url https://github.com/MIT-Lu-Lab/MIPLIB-Infeas/releases/download/v1.0 \
  --site-url https://mit-lu-lab.github.io/MIPLIB-Infeas
```

Without `--release-base-url` the download links render as disabled placeholders,
which is what you want when checking a layout change locally. Then
`python -m http.server -d _site`.

## Checks

```bash
pip install pytest ruff pyright jsonschema
pytest -q          # 110 tests, no network, no dataset
ruff check .
pyright
```

CI runs all three on every push, then builds the site twice and diffs the two
builds: the pages carry no timestamp or counter, so a second build over the first
must leave every byte alone.

## Changing the published set

Only these need a checkout of the published files:

```bash
python scripts/add_checksums.py --dataset-dir dataset      # sha256 + size into sidecars
python scripts/build_site_index.py --dataset-dir dataset   # sidecars -> metadata/site-index.json
```

`scripts/build_site_index.py` is the only thing in the repository that opens a
published file. If you change what the pages show, change `to_record` in
`website/records.py`, bump `INDEX_VERSION`, and regenerate: a build refuses an
index it would misread rather than rendering whatever the old keys happen to hold.

`schema/meta.schema.json` describes the sidecars. Keep it in step with what the
miners write; all 334 published sidecars validate against it today.

## Conventions

- **No em dashes** anywhere in rendered output, and no `&mdash;`. Tests enforce it.
- **No size class.** `Small`/`Medium`/`Large` is MIPLIB's difficulty rating for the
  *source* instance and says nothing about the published LP. Tests enforce it.
- **Counts read "N instances"**, not "N samples".
- Colour names a subset: blue is primal-infeasible, orange is dual-infeasible,
  green is what belongs to both. Everything resolves through `--view`; do not reach
  for `--primal` directly.
- The generator takes no dependencies. If something seems to need one, it probably
  needs less code instead.

## Reporting a problem with an instance

If a published file does not have the status it claims, or a source instance
carries terms other than MIPLIB's default, open an issue. The affected file will be
corrected or withdrawn.
