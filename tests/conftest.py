import json

import pytest

from website.domain import source_terms
from website.index import INDEX_VERSION, to_record
from website.render.shell import page as render_page
from website.sidecar import sample_from_meta

# Sidecars as the miners write them. The fixture projects them the way
# scripts/build_site_index.py does, so a test exercises the same path the
# published index came through rather than a hand-written record.
_SIDECARS = [
    (
        {
            "instance": "bbb",
            "sample_kind": "pruned_infeasible_sibling",
            "n_vars": 10,
            "n_cons": 4,
            "nnz": 20,
            "depth": 3,
            "branch_var": 1,
            "branch_sense": ">=",
            "branch_value": 2.0,
            "path_entries": ["x1>=2"],
            "sha256": "ab" * 32,
            "source_terms": source_terms("bbb", None),
        },
        1024,
        200,
    ),
    (
        {
            "instance": "aaa",
            "sample_kind": "pruned_infeasible_sibling",
            "n_vars": 7,
            "n_cons": 2,
            "nnz": 9,
            "depth": 1,
            "branch_var": 0,
            "branch_sense": "<=",
            "branch_value": 0.0,
            "path_entries": [],
            "sha256": "cd" * 32,
            "source_terms": source_terms("aaa", "Imported from MIPLIB2010."),
        },
        512,
        180,
    ),
    (
        {
            "instance": "aaa",
            "sample_kind": "lp_unbounded_after_drop",
            "n_vars": 7,
            "n_cons": 1,
            "nnz": 5,
            "natural_unbounded": False,
            "n_rounds": 9,
            "drops": [
                {
                    "kind": "row",
                    "row": 0,
                    "name": "c0",
                    "original_sense": "L",
                    "original_rhs": 12.0,
                    "original_range": None,
                }
            ],
            "sha256": "ef" * 32,
            "source_terms": source_terms("aaa", "Imported from MIPLIB2010."),
        },
        256,
        160,
    ),
]


def write_index(path, sidecars=None):
    """Write a site index holding these sidecars, and return its path."""
    records = [
        to_record(sample_from_meta(m, file_bytes, meta_bytes))
        for m, file_bytes, meta_bytes in (sidecars or _SIDECARS)
    ]
    records.sort(key=lambda r: (r["subset"], r["instance"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": INDEX_VERSION, "records": records}, indent=1), encoding="utf-8"
    )
    return path


@pytest.fixture
def index(tmp_path):
    """A tiny two-instance, two-subset site index under tmp_path."""
    return write_index(tmp_path / "site-index.json")


@pytest.fixture
def shell():
    """Render the document shell around a stand-in body.

    Some tests are about the document rather than the page inside it: the nav,
    the head, the skip link. about.html is only the body they hang on, so what
    that body needs is supplied here and a field added to the page is not
    added to every one of them.
    """

    def render(title: str = "Example", *, licence_href: str = "LICENSE.txt", **context) -> str:
        return render_page("about.html", title, licence_href=licence_href, software=(), **context)

    return render
