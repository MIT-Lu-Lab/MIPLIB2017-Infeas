"""Validate and atomically publish a complete static-site file set."""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

_OWNERSHIP_MARKER = PurePosixPath("site-build.json")
_OWNERSHIP_MARKER_BYTES = (
    json.dumps(
        {"generator": "miplib-infeas-site", "version": 1},
        ensure_ascii=False,
        indent=1,
    )
    + "\n"
).encode("utf-8")
_WINDOWS_RESERVED = {
    "AUX",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_WINDOWS_INVALID = frozenset('<>:"|?*')


class OutputError(RuntimeError):
    """The planned files or output location are unsafe."""


def _site_path(value: str | PurePosixPath) -> PurePosixPath:
    raw = value.as_posix() if isinstance(value, PurePosixPath) else value
    if not raw:
        raise OutputError("site paths must be non-empty strings")
    if "\\" in raw:
        raise OutputError(f"site path uses a backslash: {raw!r}")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in raw):
        raise OutputError(f"site path contains a control character: {raw!r}")

    path = PurePosixPath(raw)
    if path.is_absolute() or raw != path.as_posix():
        raise OutputError(f"site path is not canonical and relative: {raw!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise OutputError(f"site path escapes or aliases the output tree: {raw!r}")
    for part in path.parts:
        if any(char in _WINDOWS_INVALID for char in part):
            raise OutputError(f"site path is not portable to Windows: {raw!r}")
        if part.endswith((" ", ".")):
            raise OutputError(f"site path is not portable to Windows: {raw!r}")
        if part.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            raise OutputError(f"site path uses a reserved Windows name: {raw!r}")
    return path


def _prepare(
    files: Iterable[tuple[str | PurePosixPath, bytes]],
) -> tuple[tuple[PurePosixPath, bytes], ...]:
    by_path = {_OWNERSHIP_MARKER: _OWNERSHIP_MARKER_BYTES}
    portable_names = {_OWNERSHIP_MARKER.as_posix().casefold(): _OWNERSHIP_MARKER}
    for raw_path, data in files:
        path = _site_path(raw_path)
        if not isinstance(data, bytes):
            raise OutputError(f"{path}: contents must be bytes")
        portable = path.as_posix().casefold()
        if path in by_path:
            raise OutputError(f"duplicate output target: {path}")
        if portable in portable_names:
            raise OutputError(
                "output targets collide on a case-insensitive filesystem: "
                f"{portable_names[portable]} and {path}"
            )
        by_path[path] = data
        portable_names[portable] = path
    return tuple(sorted(by_path.items(), key=lambda item: item[0].as_posix()))


def _assert_owned_or_empty(root: Path) -> None:
    if root.is_symlink():
        raise OutputError(f"refusing to publish through output symlink: {root}")
    if not root.exists():
        return
    if not root.is_dir():
        raise OutputError(f"output path is not a directory: {root}")
    if not any(root.iterdir()):
        return

    marker = root.joinpath(*_OWNERSHIP_MARKER.parts)
    if marker.is_symlink() or not marker.is_file():
        raise OutputError(
            f"refusing to replace non-empty unowned output directory {root}; "
            "build into an empty directory or remove it explicitly"
        )
    try:
        marker_bytes = marker.read_bytes()
    except OSError as exc:
        raise OutputError(f"cannot read output ownership marker {marker}") from exc
    if marker_bytes != _OWNERSHIP_MARKER_BYTES:
        raise OutputError(f"unrecognised output ownership marker: {marker}")


def _write_stage(stage: Path, files: tuple[tuple[PurePosixPath, bytes], ...]) -> None:
    for path, data in files:
        target = stage.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)


def publish_atomically(
    files: Iterable[tuple[str | PurePosixPath, bytes]], out_dir: Path | str
) -> None:
    """Publish all files or leave the previous owned output tree in place."""
    prepared = _prepare(files)
    out = Path(out_dir)
    if not out.name or out == Path(out.anchor):
        raise OutputError(f"refusing to use a filesystem root as output: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    _assert_owned_or_empty(out)

    work = Path(tempfile.mkdtemp(dir=out.parent, prefix=f".{out.name}.publish-"))
    previous = work / "previous"
    try:
        stage = work / "stage"
        stage.mkdir()
        _write_stage(stage, prepared)

        try:
            if out.exists():
                out.replace(previous)
            stage.replace(out)
        except OSError as publish_error:
            if previous.exists() and not out.exists():
                try:
                    previous.replace(out)
                except OSError as restore_error:
                    raise OutputError(
                        f"could not publish site to {out}: {publish_error}; "
                        f"restoring it also failed, so the previous site is "
                        f"preserved at {previous}: {restore_error}"
                    ) from restore_error
            raise
    except OSError as exc:
        raise OutputError(f"could not publish site to {out}: {exc}") from exc
    finally:
        # Keep the only copy of the previous site if restoration failed.
        if work.exists() and (not previous.exists() or out.exists()):
            shutil.rmtree(work, ignore_errors=True)
