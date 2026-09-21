"""On-disk wallpaper catalog and gallery files."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from app.config import CATALOG_PATH, GALLERY_DIR, ensure_dirs
from app.models import WallpaperRecord

_SAFE = re.compile(r"[^A-Za-z0-9._ -]+")


def safe_name(value: str) -> str:
    cleaned = _SAFE.sub("", value).strip() or "untitled"
    return cleaned[:80]


def layout_dir(layout: str) -> Path:
    path = GALLERY_DIR / safe_name(layout)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_catalog() -> list[WallpaperRecord]:
    ensure_dirs()
    if not CATALOG_PATH.is_file():
        return []
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return [WallpaperRecord.model_validate(item) for item in raw]


def save_catalog(records: list[WallpaperRecord]) -> None:
    ensure_dirs()
    payload = [item.model_dump() for item in records]
    CATALOG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def upsert(record: WallpaperRecord) -> list[WallpaperRecord]:
    catalog = [item for item in load_catalog() if item.id != record.id]
    catalog.append(record)
    save_catalog(catalog)
    return catalog


def remove_records(ids: set[str]) -> list[WallpaperRecord]:
    return delete_records(ids)["kept"]


def _companion_paths(jpg: Path) -> list[Path]:
    return [
        jpg,
        jpg.with_suffix(".mp4"),
        jpg.with_name(jpg.stem + "_plate.jpg"),
        jpg.with_name(jpg.stem + "_chrome.png"),
    ]


def delete_records(ids: set[str]) -> dict:
    """Remove catalog rows and their JPEG / MP4 companions. Returns kept + deleted."""
    wanted = {str(item) for item in ids if item}
    catalog = load_catalog()
    keep: list[WallpaperRecord] = []
    deleted: list[str] = []
    files: list[str] = []
    titles: list[str] = []
    errors: list[str] = []
    for rec in catalog:
        if rec.id not in wanted:
            keep.append(rec)
            continue
        jpg = layout_dir(rec.layout) / rec.filename
        for path in _companion_paths(jpg):
            try:
                if path.is_file():
                    path.unlink()
                    files.append(path.name)
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        deleted.append(rec.id)
        titles.append(rec.title)
    save_catalog(keep)
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
    folder = layout_dir(layout)
    target = (folder / filename).resolve()
    if not str(target).startswith(str(folder.resolve())):
        return None
    return target if target.is_file() else None


def copy_into_gallery(src: Path, layout: str, filename: str) -> Path:
    dest = layout_dir(layout) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest
