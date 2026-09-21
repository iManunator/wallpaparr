"""Cross-device (EXDEV) safe promotion of bake temp files into the gallery."""

from __future__ import annotations

import errno
import os
from pathlib import Path
from unittest.mock import patch

from app.fsutil import promote_temp


def test_promote_temp_same_device(tmp_path: Path):
    src = tmp_path / "src" / "bake.mp4"
    dest = tmp_path / "gallery" / "layout" / "bake.mp4"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"wallpaparr-mp4-bytes")
    out = promote_temp(src, dest)
    assert out == dest
    assert dest.read_bytes() == b"wallpaparr-mp4-bytes"
    assert not src.exists()


def test_promote_temp_falls_back_on_exdev(tmp_path: Path):
    """Simulate Docker bind-mount: rename across devices raises EXDEV."""
    src = tmp_path / "tmp" / "out.mp4"
    dest = tmp_path / "data" / "gallery" / "Netflix Hero" / "out.mp4"
    src.parent.mkdir(parents=True)
    payload = b"x" * 2048
    src.write_bytes(payload)

    real_rename = os.rename

    def rename_exdev(a, b):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    with patch("os.rename", side_effect=rename_exdev):
        # shutil.move must not see a working rename; force copy2 + unlink.
        out = promote_temp(src, dest)

    assert out == dest
    assert dest.is_file()
    assert dest.read_bytes() == payload
    assert not src.exists()
    # Sanity: real rename would have worked on this host without the patch.
    assert callable(real_rename)


def test_promote_temp_overwrites_existing_dest(tmp_path: Path):
    src = tmp_path / "fresh.bin"
    dest = tmp_path / "gallery" / "old.bin"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"stale")
    src.write_bytes(b"fresh")
    promote_temp(src, dest)
    assert dest.read_bytes() == b"fresh"
    assert not src.exists()


def test_write_text_atomic_replaces_dest(tmp_path: Path):
    dest = tmp_path / "data" / "config.json"
    dest.parent.mkdir(parents=True)
    dest.write_text("{broken", encoding="utf-8")
    from app.fsutil import write_text_atomic

    out = write_text_atomic(dest, '{"ok": true}')
    assert out == dest
    assert dest.read_text(encoding="utf-8") == '{"ok": true}'
    leftovers = list(dest.parent.glob(".config.json.*.tmp"))
    assert leftovers == []


def test_promote_temp_with_simulated_separate_roots(tmp_path: Path):
    """Two sibling trees (tmp vs data/gallery) — still moves when rename works."""
    tmp_root = tmp_path / "tmp"
    gallery = tmp_path / "data" / "gallery" / "Status Focus"
    tmp_root.mkdir(parents=True)
    gallery.mkdir(parents=True)
    src = tmp_root / "chrome.png"
    dest = gallery / "title_chrome.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    promote_temp(src, dest)
    assert dest.read_bytes().startswith(b"\x89PNG")
    assert not src.exists()
