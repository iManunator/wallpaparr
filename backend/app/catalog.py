"""On-disk wallpaper catalog and gallery files."""

from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path

from app.config import CATALOG_PATH, GALLERY_DIR, ensure_dirs
from app.fsutil import write_text_atomic
from app.models import WallpaperRecord

_SAFE = re.compile(r"[^A-Za-z0-9._ -]+")
_LOCK = threading.Lock()


def safe_name(value: str) -> str:
    cleaned = _SAFE.sub("", value).strip() or "untitled"
    return cleaned[:80]


def layout_dir(layout: str, *, create: bool = True) -> Path:
    path = GALLERY_DIR / safe_name(layout)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _load_unlocked() -> list[WallpaperRecord]:
    ensure_dirs()
    if not CATALOG_PATH.is_file():
        return []
    try:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    records: list[WallpaperRecord] = []
    for item in raw:
        try:
            records.append(WallpaperRecord.model_validate(item))
        except (ValueError, TypeError):
            continue
    return records


def load_catalog() -> list[WallpaperRecord]:
    with _LOCK:
        return _load_unlocked()


def _save_unlocked(records: list[WallpaperRecord]) -> None:
    ensure_dirs()
    payload = [item.model_dump() for item in records]
    write_text_atomic(CATALOG_PATH, json.dumps(payload, indent=2))


def save_catalog(records: list[WallpaperRecord]) -> None:
    with _LOCK:
        _save_unlocked(records)


def upsert(record: WallpaperRecord) -> list[WallpaperRecord]:
    with _LOCK:
        catalog = [item for item in _load_unlocked() if item.id != record.id]
        catalog.append(record)
        _save_unlocked(catalog)
        return catalog


def remove_records(
    ids: set[str],
    *,
    delete_files: bool = True,
    keep_files: set[str] | None = None,
) -> list[WallpaperRecord]:
    return delete_records(ids, delete_files=delete_files, keep_files=keep_files)["kept"]


def _companion_paths(jpg: Path) -> list[Path]:
    return [
        jpg,
        jpg.with_suffix(".mp4"),
        jpg.with_name(jpg.stem + "_plate.jpg"),
        jpg.with_name(jpg.stem + "_chrome.png"),
    ]


def _gallery_filename(filename: str) -> str | None:
    """Basename only — catalog rows must not be able to escape the layout folder."""
    name = Path(str(filename or "")).name
    if not name or name in {".", ".."}:
        return None
    return name


def delete_records(
    ids: set[str],
    *,
    delete_files: bool = True,
    keep_files: set[str] | None = None,
) -> dict:
    """Remove catalog rows and their JPEG / MP4 companions. Returns kept + deleted."""
    wanted = {str(item) for item in ids if item}
    keep_names = {_gallery_filename(name) for name in (keep_files or set())}
    keep_names.discard(None)
    with _LOCK:
        catalog = _load_unlocked()
        keep: list[WallpaperRecord] = []
        deleted: list[str] = []
        files: list[str] = []
        titles: list[str] = []
        errors: list[str] = []
        for rec in catalog:
            if rec.id not in wanted:
                keep.append(rec)
                continue
            if delete_files:
                name = _gallery_filename(rec.filename)
                if name and name not in keep_names:
                    folder = layout_dir(rec.layout, create=False)
                    if folder.is_dir():
                        folder_resolved = folder.resolve()
                        jpg = folder / name
                        for path in _companion_paths(jpg):
                            try:
                                resolved = path.resolve()
                                if not resolved.is_relative_to(folder_resolved):
                                    continue
                                if resolved.is_file():
                                    resolved.unlink()
                                    files.append(path.name)
                            except OSError as exc:
                                errors.append(f"{path.name}: {exc}")
            deleted.append(rec.id)
            titles.append(rec.title)
        _save_unlocked(keep)
    missing = sorted(wanted - set(deleted))
    return {
        "kept": keep,
        "deleted": deleted,
        "files": files,
        "titles": titles,
        "missing": missing,
        "errors": errors,
        "skipped_pinned": [],
        "skipped_titles": [],
    }


def delete_all(*, include_pins: bool = False, layout: str | None = None) -> dict:
    """Clear the gallery. Pinned rows are kept unless include_pins is true."""
    catalog = load_catalog()
    layout_key = (layout or "").strip().lower()
    wanted: set[str] = set()
    skipped: list[str] = []
    skipped_titles: list[str] = []
    for rec in catalog:
        if layout_key and rec.layout.lower() != layout_key:
            continue
        if rec.pinned and not include_pins:
            skipped.append(rec.id)
            skipped_titles.append(rec.title)
            continue
        wanted.add(rec.id)
    if not wanted:
        return {
            "kept": catalog,
            "deleted": [],
            "files": [],
            "titles": [],
            "missing": [],
            "errors": [],
            "skipped_pinned": skipped,
            "skipped_titles": skipped_titles,
        }
    out = delete_records(wanted)
    out["skipped_pinned"] = skipped
    out["skipped_titles"] = skipped_titles
    return out


def layouts_with_images(catalog: list[WallpaperRecord] | None = None) -> list[str]:
    records = catalog if catalog is not None else load_catalog()
    names = sorted({rec.layout for rec in records if rec.filename}, key=str.lower)
    return names


def wallpaper_file(layout: str, filename: str) -> Path | None:
    """Resolve a still/MP4 inside a layout folder. Rejects path traversal.

    ``Path.name`` drops any directory components so ``../`` and absolute
    paths cannot escape. ``is_relative_to`` is the remaining belt: a naive
    ``str.startswith`` check would treat ``Netflix Hero-extra/`` as inside
    ``Netflix Hero/``.
    """
    name = Path(str(filename or "")).name
    if not name or name in {".", ".."}:
        return None
    folder = layout_dir(layout, create=False)
    if not folder.is_dir():
        return None
    folder_resolved = folder.resolve()
    target = (folder / name).resolve()
    if not target.is_relative_to(folder_resolved):
        return None
    return target if target.is_file() else None


def copy_into_gallery(src: Path, layout: str, filename: str) -> Path:
    name = _gallery_filename(filename)
    if not name:
        raise ValueError("Invalid filename")
    dest = layout_dir(layout) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    folder_resolved = layout_dir(layout, create=False).resolve()
    if not dest.resolve().is_relative_to(folder_resolved):
        raise ValueError("Invalid filename")
    shutil.copy2(src, dest)
    return dest
