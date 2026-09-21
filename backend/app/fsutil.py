"""Filesystem helpers that survive Docker bind-mounts (EXDEV)."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def promote_temp(src: Path | str, dest: Path | str) -> Path:
    """Move ``src`` onto ``dest``, even across devices.

    ``Path.replace`` / ``os.rename`` raise ``[Errno 18] Invalid cross-device link``
    when promoting bake output from container ``/tmp`` onto a bind-mounted
    gallery volume (``/data/gallery/...``). ``shutil.move`` renames when possible
    and falls back to copy2 + unlink on EXDEV — the right behavior for MP4 /
    plate / chrome promotion into the data volume.
    """
    src_path = Path(src)
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    # str() keeps shutil.move on the POSIX rename→copy path (not Path.replace).
    shutil.move(str(src_path), str(dest_path))
    return dest_path


def write_text_atomic(dest: Path | str, text: str, *, encoding: str = "utf-8") -> Path:
    """Write ``text`` onto ``dest`` via a sibling tempfile + ``promote_temp``.

    Catalog and settings JSON used to ``Path.write_text`` in place. A crash or
    full disk mid-write left a truncated file that then 500'd every API call.
    The tempfile lives next to ``dest`` so bind-mounted data volumes stay on
    the same device whenever possible.

    The name includes a random mkstemp suffix so two threads in this process
    cannot truncate each other's tempfile (pid-only names collided).
    """
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{dest_path.name}.",
        suffix=".tmp",
        dir=str(dest_path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            fd = -1  # ownership transferred to the handle
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        return promote_temp(tmp_path, dest_path)
    except Exception:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        tmp_path.unlink(missing_ok=True)
        raise
