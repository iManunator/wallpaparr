"""Filesystem helpers that survive Docker bind-mounts (EXDEV)."""

from __future__ import annotations

import shutil
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
