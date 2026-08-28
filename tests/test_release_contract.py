"""Release bytes, scientific results and deployment share one strict boundary."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from scripts import build_release_archives as archives
from scripts import release_contract as contract
from scripts import verify_published as scientific
from scripts import verify_release_assets as release
from scripts.dataset import DatasetEntry
from website.index import load_collection

SHA_A = "a" * 64
SHA_B = "b" * 64
COMMIT = "c" * 40
ROOT = Path(__file__).resolve().parents[1]


def manifest_document():
    return {
        "manifest_version": "1.0.0",
        "dataset": "MIPLIB2017-Infeas",
        "release": {"tag": "v1.0.1", "source_commit": COMMIT},
        "sidecar_schema": "meta.schema.json",
        "artifacts": [
            {"name": "sample_if.mps.gz", "role": "instance", "bytes": 3, "sha256": SHA_A},
            {"name": "sample_if.meta.json", "role": "sidecar", "bytes": 2, "sha256": SHA_B},
            {"name": "meta.schema.json", "role": "schema", "bytes": 5, "sha256": SHA_A},
            {"name": "LICENSE.txt", "role": "notice", "bytes": 7, "sha256": SHA_B},
            {"name": "verify-published.csv", "role": "verification", "bytes": 9, "sha256": SHA_A},
        ],
    }


def remote_asset(item):
    return release.Asset(item["name"], item["bytes"], item["sha256"])


def test_legacy_index_defines_the_real_673_asset_inventory():
    contract = release.expected(load_collection(ROOT / "metadata" / "site-index.json"))
    assert len(contract) == 673
    assert sum(name.endswith(".mps.gz") for name in contract) == 334
    assert sum(name.endswith(".meta.json") for name in contract) == 334
    assert {
        "primal-infeasible.zip",
        "dual-infeasible.zip",
        "primal-infeasible.csv",
        "dual-infeasible.csv",
        "LICENSE.txt",
    } <= set(contract)


def test_legacy_gate_rejects_state_inventory_size_and_digest_drift():
    baseline = {
        "sample_if.mps.gz": release.ExpectedAsset(3, SHA_A),
        "sample_if.meta.json": release.ExpectedAsset(2),
    }
    published = release.Release(
        tag="v1.0",
        draft=True,
        prerelease=True,
        assets=(
            release.Asset("sample_if.mps.gz", 4, SHA_B),
            release.Asset("unexpected.txt", 1, SHA_A),
        ),
    )

    problems = release.verify(published, "v1.0", baseline)

    assert "release is still a draft" in problems
    assert "release is marked as a prerelease" in problems
    assert any("sample_if.meta.json: missing" in problem for problem in problems)
    assert any("unexpected.txt: unexpected" in problem for problem in problems)
    assert any("records 3 B" in problem for problem in problems)
    assert any("index/notice SHA-256" in problem for problem in problems)


def test_every_remote_asset_needs_a_github_sha256():
    baseline = {"sample_if.mps.gz": release.ExpectedAsset(3, SHA_A)}
    published = release.Release(
        "v1.0",
        False,
        False,
        (release.Asset("sample_if.mps.gz", 3, None),),
    )
    assert any(
        "no valid SHA-256" in problem for problem in release.verify(published, "v1.0", baseline)
    )


def test_a_run_naming_no_tag_checks_the_release_that_needs_no_manifest():
    """The CLI retains the historical default for direct legacy runs."""
    assert release.parse_args(["--repo", "owner/repo"]).tag == release.LEGACY_TAG


def test_only_legacy_v1_may_omit_a_manifest(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_release_assets.py",
            "--repo",
            "owner/repo",
            "--tag",
            "v1.0.1",
        ],
    )
    with pytest.raises(SystemExit, match="2"):
        release.main()
    assert "only v1.0 may be verified without --manifest" in capsys.readouterr().err


def test_manifest_is_exact_but_does_not_hash_itself(tmp_path):
    document = manifest_document()
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    manifest = contract.load_manifest(path)
    manifest_asset = release.Asset.of(path)
    assets = tuple(remote_asset(item) for item in document["artifacts"])
    published = release.Release(
        "v1.0.1",
        False,
        False,
        (*assets, manifest_asset),
    )
    baseline = {
        "sample_if.mps.gz": release.ExpectedAsset(3, SHA_A),
        "sample_if.meta.json": release.ExpectedAsset(2),
        "LICENSE.txt": release.ExpectedAsset(None),
    }

    assert (
        release.verify(
            published,
            "v1.0.1",
            baseline,
            manifest=manifest,
            manifest_asset=manifest_asset,
            tag_commit=COMMIT,
        )
        == []
    )

    recursive = copy.deepcopy(document)
    recursive["artifacts"].append(
        {
            "name": path.name,
            "role": "index",
            "bytes": path.stat().st_size,
            "sha256": manifest_asset.sha256,
        }
    )
    recursive_manifest = contract.parse_manifest(recursive)
    problems = release.verify(
        published,
        "v1.0.1",
        baseline,
        manifest=recursive_manifest,
        manifest_asset=manifest_asset,
        tag_commit=COMMIT,
    )
    assert "the manifest must not list and recursively hash itself" in problems


def test_manifest_must_agree_with_the_site_index(tmp_path):
    document = manifest_document()
    document["artifacts"][0]["role"] = "archive"
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    manifest_asset = release.Asset.of(path)
    published = release.Release(
        "v1.0.1",
        False,
        False,
        (*(remote_asset(item) for item in document["artifacts"]), manifest_asset),
    )

    problems = release.verify(
        published,
        "v1.0.1",
        {"sample_if.mps.gz": release.ExpectedAsset(4, SHA_B, "instance")},
        manifest=contract.parse_manifest(document),
        manifest_asset=manifest_asset,
        tag_commit=COMMIT,
    )

    assert len(problems) == 3
    assert any("manifest records 3 B, index/notice records 4 B" in p for p in problems)
    assert any(f"manifest SHA-256 {SHA_A}, index/notice SHA-256 {SHA_B}" in p for p in problems)
    assert any("manifest role 'archive', expected 'instance'" in p for p in problems)


def test_manifest_rejects_legal_conclusions_and_duplicate_names():
    legal = manifest_document()
    legal["license"] = "CC-BY-SA-4.0"
    with pytest.raises(ValueError, match="license"):
        contract.parse_manifest(legal)

    duplicate = manifest_document()
    duplicate["artifacts"].append(copy.deepcopy(duplicate["artifacts"][0]))
    with pytest.raises(ValueError, match="more than once"):
        contract.parse_manifest(duplicate)


def test_manifest_file_is_strict_json(tmp_path):
    path = tmp_path / "release-manifest.json"
    path.write_text('{"manifest_version": "1", "manifest_version": "1"}', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate object key"):
        contract.load_manifest(path)


def test_manifest_requires_scientific_evidence_and_a_bound_sidecar_schema():
    no_evidence = manifest_document()
    no_evidence["artifacts"] = [
        item for item in no_evidence["artifacts"] if item["role"] != "verification"
    ]
    with pytest.raises(ValueError, match=r"manifest\.artifacts"):
        contract.parse_manifest(no_evidence)

    missing_schema = manifest_document()
    missing_schema["sidecar_schema"] = "missing.schema.json"
    with pytest.raises(ValueError, match="not present"):
        contract.parse_manifest(missing_schema)


def test_failed_archive_build_leaves_the_published_zip_unchanged(tmp_path):
    out = tmp_path / "primal-infeasible.zip"
    out.write_bytes(b"previous archive")

    with pytest.raises(FileNotFoundError):
        archives.write_archive(out, ((tmp_path / "missing.mps.gz", "missing.mps.gz"),))

    assert out.read_bytes() == b"previous archive"
    assert not list(tmp_path.glob(".primal-infeasible.*.zip"))


def test_scientific_report_binds_the_result_to_input_bytes(tmp_path, monkeypatch):
    sample = tmp_path / "sample_if.mps.gz"
    sample.write_bytes(b"mps")
    monkeypatch.setattr(
        scientific,
        "classify",
        lambda *_: scientific.SolveResult("infeasible", read_warning=True),
    )

    row = scientific._check(
        scientific.CheckJob(
            "primal",
            sample,
            30.0,
            (3, hashlib.sha256(b"mps").hexdigest()),
        )
    )
    csv_row = scientific._csv_row(row, "1.2.3")

    assert row.ok is True
    assert row.file_bytes == 3
    assert row.sha256 == hashlib.sha256(b"mps").hexdigest()
    assert row.manifest_ok is True
    assert csv_row["got"] == "infeasible (read warning)"
    assert (csv_row["solver"], csv_row["threads"]) == ("HiGHS", 1)


def test_scientific_manifest_inventory_must_match_local_mps(tmp_path):
    path = tmp_path / "sample_if.mps.gz"
    path.write_bytes(b"mps")
    manifest = contract.parse_manifest(manifest_document())
    entry = DatasetEntry("primal", "sample", path, tmp_path / "sample_if.meta.json")

    assert scientific.manifest_instances(
        manifest,
        [entry],
    ) == {"sample_if.mps.gz": (3, SHA_A)}

    with pytest.raises(ValueError, match="differs from the dataset"):
        scientific.manifest_instances(manifest, [])


def test_scientific_report_requires_a_solver_version(monkeypatch):
    def missing_version(_package):
        raise scientific.importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(scientific.importlib.metadata, "version", missing_version)
    with pytest.raises(SystemExit, match="cannot determine the HiGHS version"):
        scientific._highspy_version()


def test_pages_deployment_has_a_release_gate_before_deploy():
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    scheduled = (workflows / "verify-release.yml").read_text(encoding="utf-8")
    ci = (workflows / "ci.yml").read_text(encoding="utf-8")
    assert "workflow_call:" in scheduled
    assert "pip install --group contracts" in scheduled
    assert "uses: ./.github/workflows/verify-release.yml" in ci
    assert "needs: release-gate" in ci
    assert "uses: actions/deploy-pages@v5" in ci
