"""The file tools must never bin, move or overwrite a whole important folder."""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from deskbuddy.files import paths, tools
from deskbuddy.files.tools import file_delete, file_delete_forever, file_move, file_write


@pytest.fixture
def home(tmp_path, monkeypatch):
    fake = tmp_path / "home"
    for name in paths.KNOWN.values():
        (fake / name).mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake))
    return fake


@pytest.fixture
def ctx(tmp_path):
    memory = SimpleNamespace(add_undo=lambda *a, **k: None)
    return SimpleNamespace(memory=memory, settings=SimpleNamespace(data_dir=tmp_path), job_id=1)


@pytest.fixture
def fake_trash(monkeypatch):
    monkeypatch.setattr(tools, "send2trash", lambda p: Path(p).unlink())


def test_delete_desktop_refused(home, ctx, fake_trash):
    out = file_delete(ctx, "Desktop")
    assert not out.ok and "Desktop" in out.text
    assert (home / "Desktop").is_dir()


def test_delete_empty_path_refused(home, ctx, fake_trash):
    for text in ("", "   ", "."):
        assert not file_delete(ctx, text).ok
        assert not file_delete_forever(ctx, text).ok
    assert (home / "Desktop").is_dir()


def test_delete_normal_file_still_works(home, ctx, fake_trash):
    (home / "Desktop" / "a.txt").write_text("x")
    assert file_delete(ctx, "Desktop/a.txt").ok
    assert not (home / "Desktop" / "a.txt").exists()


def test_move_documents_refused(home, ctx):
    out = file_move(ctx, "Documents", str(home / "Elsewhere"))
    assert not out.ok
    assert (home / "Documents").is_dir()


def test_write_and_home_refused(home, ctx):
    assert not file_write(ctx, "Downloads", "x").ok
    assert not file_delete_forever(ctx, str(home)).ok
    assert home.is_dir()


def test_protected_is_a_real_prefix_check(monkeypatch):
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    assert paths.protected(Path(r"C:\Windows\System32"))
    assert not paths.protected(Path(r"C:\Windows2"))
    assert not paths.protected(Path(r"C:\WindowsApps-foo"))
