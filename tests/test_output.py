import json
from pathlib import Path

import pytest

from website.output import OutputError, publish_atomically


def _files(text: str):
    return [("index.html", text.encode("utf-8"))]


def test_publish_writes_a_complete_owned_tree(tmp_path):
    out = tmp_path / "site"
    publish_atomically(_files("hello"), out)

    assert (out / "index.html").read_text(encoding="utf-8") == "hello"
    marker = json.loads((out / "site-build.json").read_text(encoding="utf-8"))
    assert marker == {"generator": "miplib-infeas-site", "version": 1}


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute",
        "../escape",
        "a/../escape",
        "./alias",
        "a//alias",
        "back\\slash",
        "C:/escape",
        "bad:name",
        "bad?name",
        "CON.txt",
        "trailing.",
        "control\x00name",
    ],
)
def test_publish_rejects_unsafe_or_nonportable_paths(tmp_path, path):
    out = tmp_path / "site"
    with pytest.raises(OutputError):
        publish_atomically([(path, b"x")], out)
    assert not out.exists()


def test_publish_rejects_duplicate_and_portable_name_collisions(tmp_path):
    with pytest.raises(OutputError, match="duplicate"):
        publish_atomically([("same", b"one"), ("same", b"two")], tmp_path / "one")
    with pytest.raises(OutputError, match="case-insensitive"):
        publish_atomically([("Page.html", b"one"), ("page.html", b"two")], tmp_path / "two")


def test_callers_cannot_override_the_ownership_marker(tmp_path):
    with pytest.raises(OutputError, match="duplicate"):
        publish_atomically([("site-build.json", b"{}")], tmp_path / "site")


def test_publish_refuses_an_unrecognised_ownership_marker(tmp_path):
    out = tmp_path / "site"
    publish_atomically(_files("old"), out)
    (out / "site-build.json").write_text("{}", encoding="utf-8")

    with pytest.raises(OutputError, match="unrecognised"):
        publish_atomically(_files("new"), out)

    assert (out / "index.html").read_text(encoding="utf-8") == "old"


def test_publish_refuses_a_filesystem_root(tmp_path):
    """The guard that stands between a mistyped --out-dir and the whole disk.
    It has to refuse before anything is created, not after."""
    root = Path(tmp_path.anchor)
    with pytest.raises(OutputError, match="filesystem root"):
        publish_atomically(_files("hello"), root)


def test_publish_refuses_to_follow_an_output_symlink(tmp_path):
    """Publishing replaces the directory it is given. Following a link would
    replace something else, which is the one mistake with no undo."""
    real = tmp_path / "elsewhere"
    real.mkdir()
    (real / "keep.txt").write_text("keep", encoding="utf-8")
    link = tmp_path / "site"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("this platform does not let the test create a symlink")

    with pytest.raises(OutputError, match="symlink"):
        publish_atomically(_files("hello"), link)
    assert (real / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_publish_refuses_an_output_path_that_is_a_file(tmp_path):
    out = tmp_path / "site"
    out.write_text("not a directory", encoding="utf-8")
    with pytest.raises(OutputError, match="not a directory"):
        publish_atomically(_files("hello"), out)
    assert out.read_text(encoding="utf-8") == "not a directory"


def test_publish_refuses_contents_that_are_not_bytes(tmp_path):
    out = tmp_path / "site"
    with pytest.raises(OutputError, match="must be bytes"):
        publish_atomically([("index.html", "text, not bytes")], out)
    assert not out.exists()


def test_an_unreadable_ownership_marker_is_not_taken_as_permission(tmp_path, monkeypatch):
    """Refusing to replace an unowned tree must not turn into permission to
    replace it the moment the marker cannot be read."""
    out = tmp_path / "site"
    publish_atomically(_files("first"), out)

    def unreadable(*_args, **_kwargs):
        raise OSError("marker unreadable")

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    with pytest.raises(OutputError, match="cannot read output ownership marker"):
        publish_atomically(_files("second"), out)


def test_publish_refuses_a_nonempty_unowned_directory(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    foreign = out / "notes.txt"
    foreign.write_text("mine", encoding="utf-8")

    with pytest.raises(OutputError, match="unowned"):
        publish_atomically(_files("new"), out)

    assert foreign.read_text(encoding="utf-8") == "mine"
    assert not (out / "index.html").exists()


def test_republish_replaces_the_whole_owned_tree(tmp_path):
    out = tmp_path / "site"
    publish_atomically(_files("old"), out)
    (out / "stale.txt").write_text("stale", encoding="utf-8")

    publish_atomically(_files("new"), out)

    assert (out / "index.html").read_text(encoding="utf-8") == "new"
    assert not (out / "stale.txt").exists()


def test_failed_promotion_restores_the_previous_tree(tmp_path, monkeypatch):
    out = tmp_path / "site"
    publish_atomically(_files("old"), out)
    original_replace = Path.replace

    def fail_stage_promotion(self, target):
        if self.name == "stage" and Path(target) == out:
            raise OSError("injected promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_stage_promotion)
    with pytest.raises(OutputError, match="injected promotion failure"):
        publish_atomically(_files("new"), out)

    assert (out / "index.html").read_text(encoding="utf-8") == "old"
    assert not list(tmp_path.glob(".site.*"))


def test_failed_restoration_preserves_the_previous_tree(tmp_path, monkeypatch):
    out = tmp_path / "site"
    publish_atomically(_files("old"), out)
    original_replace = Path.replace

    def fail_promotion_and_restore(self, target):
        if self.name in {"stage", "previous"} and Path(target) == out:
            raise OSError(f"injected {self.name} failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_promotion_and_restore)
    with pytest.raises(OutputError, match="previous site is preserved"):
        publish_atomically(_files("new"), out)

    backups = list(tmp_path.glob(".site.publish-*/previous"))
    assert len(backups) == 1
    assert (backups[0] / "index.html").read_text(encoding="utf-8") == "old"
