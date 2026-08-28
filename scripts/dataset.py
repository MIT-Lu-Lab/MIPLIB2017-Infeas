"""The on-disk layout shared by dataset maintenance commands."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from website.domain import SUBSET_SPECS, Subset
from website.jsonio import JsonError, read_json


class DatasetError(ValueError):
    """The published dataset layout or one of its editable sidecars is malformed."""


@dataclass(frozen=True)
class DatasetEntry:
    """The published MPS and sidecar for one subset instance."""

    subset: Subset
    instance: str
    mps: Path
    sidecar: Path

    @property
    def stem(self) -> str:
        return self.mps.name.removesuffix(".mps.gz")


def scan_dataset(dataset_dir: Path) -> tuple[DatasetEntry, ...]:
    """Discover every paired dataset entry in stable publication order."""

    found: list[DatasetEntry] = []
    for subset, spec in SUBSET_SPECS.items():
        directory = dataset_dir / spec.directory
        if not directory.is_dir():
            raise DatasetError(f"{directory}: not a directory")

        mps_tail = f"{spec.suffix}.mps.gz"
        sidecar_tail = f"{spec.suffix}.meta.json"
        mps_files = sorted(directory.glob("*.mps.gz"))
        sidecar_files = sorted(directory.glob("*.meta.json"))

        wrong = [path for path in mps_files if not path.name.endswith(mps_tail)]
        wrong += [path for path in sidecar_files if not path.name.endswith(sidecar_tail)]
        if wrong:
            path = wrong[0]
            raise DatasetError(
                f"{path}: filename does not carry the {spec.label} suffix {spec.suffix!r}"
            )

        by_instance_mps = {path.name[: -len(mps_tail)]: path for path in mps_files}
        by_instance_sidecar = {path.name[: -len(sidecar_tail)]: path for path in sidecar_files}
        missing_sidecars = sorted(set(by_instance_mps) - set(by_instance_sidecar))
        missing_models = sorted(set(by_instance_sidecar) - set(by_instance_mps))
        if missing_sidecars:
            path = by_instance_mps[missing_sidecars[0]]
            raise DatasetError(f"{path}: no sidecar beside it")
        if missing_models:
            path = by_instance_sidecar[missing_models[0]]
            raise DatasetError(f"{path}: no .mps.gz beside it")

        for instance in sorted(by_instance_mps):
            if not instance:
                raise DatasetError(f"{directory}: an instance name cannot be empty")
            found.append(
                DatasetEntry(
                    subset=subset,
                    instance=instance,
                    mps=by_instance_mps[instance],
                    sidecar=by_instance_sidecar[instance],
                )
            )
    return tuple(found)


def read_sidecar(path: Path) -> dict[str, Any]:
    """Read one sidecar as strict JSON before a maintenance command edits it."""

    try:
        document = read_json(path)
    except JsonError as exc:
        raise DatasetError(str(exc)) from exc
    if not isinstance(document, dict):
        raise DatasetError(f"{path}: sidecar must be a JSON object")
    return cast(dict[str, Any], document)


def read_entry_sidecar(entry: DatasetEntry) -> dict[str, Any]:
    """Read a sidecar and bind its identity to the filename and subset directory."""

    document = read_sidecar(entry.sidecar)
    if document.get("instance") != entry.instance:
        raise DatasetError(f"{entry.sidecar}: instance does not match its filename")
    expected_kind = SUBSET_SPECS[entry.subset].kind
    if document.get("sample_kind") != expected_kind:
        raise DatasetError(f"{entry.sidecar}: sample_kind does not match its subset directory")
    return document


def sidecar_text(document: object) -> str:
    """Serialize a sidecar in the canonical published layout."""

    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def replace_sidecar(path: Path, document: object) -> None:
    """Atomically replace one sidecar with its canonical serialization."""

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
            newline="\n",
        ) as stream:
            temporary = Path(stream.name)
            stream.write(sidecar_text(document))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
