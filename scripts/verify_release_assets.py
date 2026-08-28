"""Verify that a GitHub Release is the exact collection the site advertises.

    python -m scripts.verify_release_assets --repo MIT-Lu-Lab/MIPLIB2017-Infeas --tag v1.0

The legacy v1.0 release predates a release manifest, so its contract comes from
the committed site index: exact asset names, both file sizes for every sample,
and the recorded SHA-256 for every MPS. GitHub must report a SHA-256 for every
asset. The notice is required by name, but is not rebound to today's LICENSE:
doing that would demand that the immutable historical release change whenever
its legal notice receives a forward correction.

Every release after v1.0 must pass ``--manifest``. In that mode the manifest is an
immutable inventory of every payload asset, including sizes and SHA-256 values;
the manifest file itself is the one deliberate exception, preventing a digest
from recursively containing itself. No manifest is inferred for v1.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.release_contract import (
    MANIFEST_ASSET_NAME,
    MANIFEST_VERSION,
    Manifest,
    load_manifest,
)
from website import INDEX_FILE
from website.domain import SUBSET_SPECS, Sample
from website.index import load_collection

API = "https://api.github.com"
LEGACY_TAG = "v1.0"
_PAYLOAD_ROLES = {
    **{f"{info.slug}.zip": "archive" for info in SUBSET_SPECS.values()},
    **{f"{info.slug}.csv": "index" for info in SUBSET_SPECS.values()},
    "LICENSE.txt": "notice",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class Asset:
    """One asset as GitHub records it."""

    name: str
    size: int
    sha256: str | None

    @classmethod
    def of(cls, path: Path) -> Asset:
        """The same measurements taken locally, to compare with what is
        published. Hashed in one pass, not held in memory."""
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        return cls(path.name, path.stat().st_size, digest)


@dataclass(frozen=True)
class Release:
    """The release state relevant to a production download prefix."""

    tag: str
    draft: bool
    prerelease: bool
    assets: tuple[Asset, ...]


@dataclass(frozen=True)
class ExpectedAsset:
    """A locally known size and/or digest; ``None`` means not known locally."""

    size: int | None
    sha256: str | None = None
    role: str | None = None


def _get_json(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "MIPLIB2017-Infeas-release-verifier",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url}: {exc.reason}") from exc


def _api_path(value: str, *, keep_slash: bool = False) -> str:
    return urllib.parse.quote(value, safe="/" if keep_slash else "")


def _github_digest(value: object) -> str | None:
    """Return the hex part of GitHub's ``sha256:<hex>`` value, if valid."""
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return None
    digest = value.removeprefix("sha256:")
    return digest if _SHA256.fullmatch(digest) else None


def fetch_release(repo: str, tag: str, token: str | None) -> Release:
    """Fetch release state and every asset, following GitHub pagination."""
    repo_path = _api_path(repo, keep_slash=True)
    release = _get_json(f"{API}/repos/{repo_path}/releases/tags/{_api_path(tag)}", token)
    if not isinstance(release, dict):
        raise RuntimeError("GitHub returned a non-object release response")

    assets: list[Asset] = []
    page = 1
    while True:
        batch = _get_json(
            f"{API}/repos/{repo_path}/releases/{release['id']}/assets?per_page=100&page={page}",
            token,
        )
        if not isinstance(batch, list):
            raise RuntimeError("GitHub returned a non-array asset response")
        if not batch:
            break
        for raw in batch:
            if not isinstance(raw, dict):
                raise RuntimeError("GitHub returned a non-object asset entry")
            assets.append(
                Asset(
                    name=str(raw.get("name", "")),
                    size=int(raw.get("size", -1)),
                    sha256=_github_digest(raw.get("digest")),
                )
            )
        page += 1

    return Release(
        tag=str(release.get("tag_name", "")),
        draft=bool(release.get("draft")),
        prerelease=bool(release.get("prerelease")),
        assets=tuple(assets),
    )


def fetch_tag_commit(repo: str, tag: str, token: str | None) -> str:
    """Resolve either a lightweight or annotated tag to its commit SHA."""
    repo_path = _api_path(repo, keep_slash=True)
    ref = _get_json(f"{API}/repos/{repo_path}/git/ref/tags/{_api_path(tag)}", token)
    if not isinstance(ref, dict) or not isinstance(ref.get("object"), dict):
        raise RuntimeError("GitHub returned a malformed tag reference")
    obj = ref["object"]
    visited: set[str] = set()
    while obj.get("type") == "tag":
        sha = str(obj.get("sha", ""))
        if not _GIT_SHA.fullmatch(sha) or sha in visited:
            raise RuntimeError("GitHub returned an invalid or cyclic annotated tag")
        visited.add(sha)
        tag_object = _get_json(f"{API}/repos/{repo_path}/git/tags/{sha}", token)
        if not isinstance(tag_object, dict) or not isinstance(tag_object.get("object"), dict):
            raise RuntimeError("GitHub returned a malformed annotated tag object")
        obj = tag_object["object"]
    sha = str(obj.get("sha", ""))
    if obj.get("type") != "commit" or not _GIT_SHA.fullmatch(sha):
        raise RuntimeError("release tag does not resolve to a 40-character commit SHA")
    return sha


def expected(samples: Sequence[Sample]) -> dict[str, ExpectedAsset]:
    """Build the non-invented v1.0 contract from the committed site index."""
    wanted: dict[str, ExpectedAsset] = {}
    for sample in samples:
        mps = f"{sample.stem}.mps.gz"
        meta = f"{sample.stem}.meta.json"
        if sample.sha256 is None:
            raise ValueError(f"{mps}: the site index has no valid SHA-256")
        wanted[mps] = ExpectedAsset(sample.file_bytes, sample.sha256, "instance")
        wanted[meta] = ExpectedAsset(sample.meta_bytes, role="sidecar")

    for name, role in _PAYLOAD_ROLES.items():
        wanted[name] = ExpectedAsset(None, role=role)
    return wanted


def _remote_assets(release: Release) -> tuple[dict[str, Asset], list[str]]:
    problems: list[str] = []
    remote: dict[str, Asset] = {}
    for asset in release.assets:
        if asset.name in remote:
            problems.append(f"release names asset {asset.name!r} more than once")
        else:
            remote[asset.name] = asset
        if asset.size < 1:
            problems.append(f"{asset.name}: GitHub reports a non-positive size")
        if asset.sha256 is None:
            problems.append(f"{asset.name}: GitHub reports no valid SHA-256 digest")
    return remote, problems


def _manifest_expectations(
    manifest: Manifest,
    baseline: dict[str, ExpectedAsset],
    manifest_asset: Asset | None,
    tag: str,
    tag_commit: str | None,
) -> tuple[dict[str, ExpectedAsset], str, list[str]]:
    problems: list[str] = []
    declared = {
        item.name: ExpectedAsset(item.size, item.sha256, item.role) for item in manifest.artifacts
    }
    for name, wanted in baseline.items():
        artifact = declared.get(name)
        if artifact is None:
            problems.append(f"{name}: required by the site index but absent from the manifest")
            continue
        if wanted.size is not None and artifact.size != wanted.size:
            problems.append(
                f"{name}: manifest records {artifact.size} B, index/notice records {wanted.size} B"
            )
        if wanted.sha256 is not None and artifact.sha256 != wanted.sha256:
            problems.append(
                f"{name}: manifest SHA-256 {artifact.sha256}, index/notice SHA-256 {wanted.sha256}"
            )
        if wanted.role is not None and artifact.role != wanted.role:
            problems.append(f"{name}: manifest role {artifact.role!r}, expected {wanted.role!r}")

    if manifest.tag != tag:
        problems.append(f"manifest release tag {manifest.tag!r}, expected {tag!r}")
    if tag_commit is None:
        problems.append("release tag commit was not resolved")
    elif manifest.source_commit != tag_commit:
        problems.append(
            f"manifest source commit {manifest.source_commit}, tag resolves to {tag_commit}"
        )

    if manifest_asset is None:
        problems.append("manifest bytes were not supplied for self verification")
        return baseline, "index/notice", problems
    if manifest_asset.name in declared:
        problems.append("the manifest must not list and recursively hash itself")
    declared[manifest_asset.name] = ExpectedAsset(manifest_asset.size, manifest_asset.sha256)
    return declared, "manifest", problems


def _compare_release(
    remote: dict[str, Asset], contract: dict[str, ExpectedAsset], source: str
) -> list[str]:
    problems: list[str] = []
    missing = sorted(set(contract) - set(remote))
    extra = sorted(set(remote) - set(contract))
    problems.extend(f"{name}: missing from the release" for name in missing)
    problems.extend(f"{name}: unexpected release asset" for name in extra)
    for name, wanted in contract.items():
        actual = remote.get(name)
        if actual is None:
            continue
        if wanted.size is not None and actual.size != wanted.size:
            problems.append(
                f"{name}: {source} records {wanted.size} B, release has {actual.size} B"
            )
        if wanted.sha256 is not None and actual.sha256 != wanted.sha256:
            problems.append(
                f"{name}: {source} SHA-256 {wanted.sha256}, release has {actual.sha256 or 'none'}"
            )
    return problems


def verify(
    release: Release,
    tag: str,
    baseline: dict[str, ExpectedAsset],
    *,
    manifest: Manifest | None = None,
    manifest_asset: Asset | None = None,
    tag_commit: str | None = None,
) -> list[str]:
    """Return every contract violation; an empty result is a deployable release."""
    problems: list[str] = []
    if release.tag != tag:
        problems.append(f"release names tag {release.tag!r}, expected {tag!r}")
    if release.draft:
        problems.append("release is still a draft")
    if release.prerelease:
        problems.append("release is marked as a prerelease")

    remote, asset_problems = _remote_assets(release)
    problems.extend(asset_problems)

    contract = baseline
    source = "index/notice"
    if manifest is not None:
        contract, source, manifest_problems = _manifest_expectations(
            manifest, baseline, manifest_asset, tag, tag_commit
        )
        problems.extend(manifest_problems)
    problems.extend(_compare_release(remote, contract, source))
    return problems


def _print_problems(problems: list[str], limit: int = 50) -> None:
    for problem in problems[:limit]:
        print(f"  - {problem}", file=sys.stderr)
    if len(problems) > limit:
        print(f"  - ... and {len(problems) - limit} more", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The command line, and the one rule relating its arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo", required=True, help="OWNER/NAME")
    # Defaulted rather than required, because the rule below already says
    # which tag a run without a manifest may name. A caller repeating it is a
    # second place to edit that nothing checks against the first.
    parser.add_argument(
        "--tag", default=LEGACY_TAG, help=f"release to check (default: {LEGACY_TAG})"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="versioned manifest for a post-v1.0 release; never inferred",
    )
    args = parser.parse_args(argv)
    if args.tag != LEGACY_TAG and args.manifest is None:
        parser.error(f"only {LEGACY_TAG} may be verified without --manifest")
    return args


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    try:
        baseline = expected(load_collection(INDEX_FILE))
        manifest = load_manifest(args.manifest) if args.manifest else None
        manifest_asset = None
        tag_commit = None
        if args.manifest:
            if args.manifest.name != MANIFEST_ASSET_NAME:
                raise ValueError(
                    f"manifest must be named {MANIFEST_ASSET_NAME!r}, got {args.manifest.name!r}"
                )
            manifest_asset = Asset.of(args.manifest)
            tag_commit = fetch_tag_commit(args.repo, args.tag, token)
        release = fetch_release(args.repo, args.tag, token)
        problems = verify(
            release,
            args.tag,
            baseline,
            manifest=manifest,
            manifest_asset=manifest_asset,
            tag_commit=tag_commit,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"release verification could not run: {exc}", file=sys.stderr)
        return 2

    contract = f"manifest {MANIFEST_VERSION}" if manifest else "legacy index"
    print(f"release {args.repo}@{args.tag}: {len(release.assets)} assets; contract: {contract}")
    if problems:
        print(f"release verification failed with {len(problems)} problem(s):", file=sys.stderr)
        _print_problems(problems)
        return 1
    print("release is published, exact, and digest-verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
