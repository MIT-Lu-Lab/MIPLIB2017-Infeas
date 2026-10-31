import re
from pathlib import Path

from website import content
from website import render as V
from website.domain import collection_totals, subset_bytes
from website.index import load_collection

ROOT = Path(__file__).resolve().parents[1]


def test_guide_links_the_machine_readable_schema():
    assert 'href="../schema/sidecar/1.1.0/meta.schema.json"' in V.render_guide(130)


def test_download_page_links_the_archives_and_indexes(index):
    samples = load_collection(index)
    html = V.render_download(
        collection_totals(samples), subset_bytes(samples), release_base_url="https://e.invalid/dl"
    )
    assert 'href="https://e.invalid/dl/primal-infeasible.zip"' in html
    assert 'href="https://e.invalid/dl/dual-infeasible.zip"' in html
    assert 'href="../primal-infeasible.csv"' in html
    assert 'href="../dual-infeasible.csv"' in html


def test_download_archive_links_disabled_without_a_release(index):
    samples = load_collection(index)
    html = V.render_download(collection_totals(samples), subset_bytes(samples))
    assert 'aria-disabled="true"' in html
    assert "https://" not in html.split("<main")[1].split("</main>")[0]


def test_overview_citation_carries_no_doi(index):
    samples = load_collection(index)
    html = V.render_overview(samples)
    citation = re.search(r'<div class="cite">(.*?)</div>', html, re.S).group(1)
    assert "doi" not in citation.lower()
    assert "howpublished" in citation
    assert "https://doi.org/10.1007/s12532-020-00194-3" in html


def test_overview_citation_uses_the_supplied_site_url(index):
    samples = load_collection(index)
    html = V.render_overview(samples, site_url="https://example.invalid/miplib2017-infeas/")
    assert "https://example.invalid/miplib2017-infeas/" in html


def test_about_credits_miplib_and_states_the_licence():
    html = V.render_about()
    assert "MIPLIB 2017" in html
    assert "CC BY-SA 4.0" in html
    # not plain CC-BY: the instances that are licensed are ShareAlike, so the
    # adaptation must be too
    assert "CC-BY 4.0" not in html
    assert "adult-max5features" in html and "BSD 3-Clause" in html
    assert 'href="../LICENSE.txt"' in html


def test_about_does_not_claim_one_licence_for_every_source_instance():
    """The page must distinguish licensed and carried-over sources."""
    html = " ".join(V.render_about().split())  # the claim may wrap mid-phrase
    assert "no licence of record" in html
    assert "carried-over sources are not" in html


def test_the_licence_grant_is_limited_to_rights_actually_held():
    """A licence can only give away what the licensor has.

    Much of what this project adds is fact rather than expression: a constraint
    matrix, a row count, a checksum. Granting CC BY-SA over those outright would
    claim a copyright that may not subsist, so the grant is qualified.
    """
    html = " ".join(V.render_about().split())
    assert "To the extent this project holds copyright or related rights" in html


def test_about_describes_both_mining_procedures():
    html = V.render_about()
    assert "branch-and-bound" in html
    assert "unbounded" in html


def test_about_names_the_solver_that_produced_the_collection():
    html = V.render_about()
    # reproducing the tree requires knowing which solver built it
    assert "CPLEX" in html
    assert "HiGHS" in html and "Gurobi" in html


def test_about_states_a_version_for_every_program_that_produced_the_files():
    """Naming a solver is half the answer; a tree is the tree its version built."""
    html = V.render_about()
    for tool in content.SOFTWARE:
        assert f'<span class="mono">{tool.name}</span>' in html
        assert f'<span class="ftype">{tool.version}</span>' in html
        assert tool.role in html


def test_the_readme_states_the_versions_the_site_states():
    """Two places, one source. A version bumped on the page and not in the
    README would leave a reader repeating the run against the wrong release,
    and nothing but a reader would notice."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for tool in content.SOFTWARE:
        assert f"| {tool.name} | {tool.version} | {tool.role} |" in readme


def test_guide_explains_integrity_and_version_fields():
    html = V.render_guide(130)
    for field in ("file_bytes", "sha256", "sample_kind_version", "schema_version"):
        assert field in html
    assert "neither is an MPS-format version" in html
    assert "x&lt;index&gt;&lt;sense&gt;&lt;value&gt;" in html
    assert "lower bound" in html and "upper bound" in html
