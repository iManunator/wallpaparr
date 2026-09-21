"""Generate stills (and optional motion) from provider media lists."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from app import catalog as catalog_store
from app.config import load_settings
from app.demo_art import logo_bytes_for_item, still_path_for_item
from app.images import looks_like_image
from app.layouts import load_layout
from app.messages import generate_message, motion_bake_message
from app.models import GenerateRequest, MediaItem, WallpaperRecord
from app.motion import generate_motion, has_motion, profile_for_wallpaper, profile_from_settings
from app.providers import HttpClient
from app.providers.demo import DemoProvider
from app.providers.jellyfin import JellyfinProvider
from app.providers.seerr import SeerrProvider
from app.providers.tmdb import TmdbProvider
from app.render import render_chrome, render_plate, render_still, save_jpeg, save_png
from app.skip import matching_records, media_ids_of, records_to_cleanup, should_skip, status_changed


def _providers_from_settings():
    settings = load_settings()
    jf = settings.jellyfin or {}
    se = settings.jellyseerr or {}
    tm = settings.tmdb or {}
    om = settings.omdb or {}
    return {
        "demo": DemoProvider(),
        "jellyfin": JellyfinProvider(url=jf.get("url") or "", api_key=jf.get("api_key") or "", user_id=jf.get("user_id") or ""),
        "jellyseerr": SeerrProvider(
            url=se.get("url") or "",
            api_key=se.get("api_key") or "",
            trending_window=se.get("trending_window") or "week",
            omdb_api_key=om.get("api_key") or "",
        ),
        "tmdb": TmdbProvider(api_key=tm.get("api_key") or "", language=tm.get("language") or "en-US"),
    }


def _list_items(provider, name: str, limit: int, category: str = "trending"):
    if name == "jellyseerr":
        return provider.list_items(limit=limit, category=category)
    return provider.list_items(limit=limit)


def collect_items(
    source: str,
    limit: int,
    warnings: list[str] | None = None,
    seerr_category: str = "trending",
) -> list[MediaItem]:
    providers = _providers_from_settings()
    key = (source or "demo").lower()
    if key in ("seerr", "jellyseerr"):
        key = "jellyseerr"
    notes = warnings if warnings is not None else []

    def warn(message: str) -> None:
        notes.append(message)

    if key == "all":
        items: list[MediaItem] = []
        for name in ("jellyfin", "jellyseerr", "demo"):
            provider = providers[name]
            if name != "demo" and not provider.is_configured():
                continue
            try:
                items.extend(_list_items(provider, name, limit, seerr_category))
            except Exception as exc:
                warn(f"{name}: {exc}")
                continue
        if not items:
            warn("No configured libraries returned titles; using the demo catalog.")
            items = providers["demo"].list_items(limit=limit)
        items = _dedupe(items)[:limit]
    else:
        provider = providers.get(key) or providers["demo"]
        items = []
        used_fallback = False
        if key != "demo" and not provider.is_configured():
            label = "Jellyfin" if key == "jellyfin" else "Jellyseerr / Seerr" if key == "jellyseerr" else key
            warn(f"{label} is not configured. Using the demo catalog.")
            used_fallback = True
            items = providers["demo"].list_items(limit=limit)
        else:
            try:
                items = _list_items(provider, key, limit, seerr_category)
            except Exception as exc:
                label = "Jellyfin" if key == "jellyfin" else "Jellyseerr / Seerr" if key == "jellyseerr" else key
                warn(f"{label} request failed: {exc}. Using the demo catalog.")
                used_fallback = True
                items = []
            if not items and key != "demo":
                if not used_fallback:
                    label = "Jellyfin" if key == "jellyfin" else "Jellyseerr / Seerr" if key == "jellyseerr" else key
                    warn(f"{label} returned no movies or series. Using the demo catalog.")
                items = providers["demo"].list_items(limit=limit)
    tmdb = providers["tmdb"]
    if tmdb.is_configured():
        items = [tmdb.enrich(item) for item in items]
    elif key in ("jellyseerr", "all") and any(
        getattr(i, "source", "") == "jellyseerr" and not i.logo_url for i in items
    ):
        warn(
            "Seerr clearlogos need a TMDB API key in Settings → TMDB "
            "(discover does not include logos). In-library Seerr titles can still use Jellyfin logos."
        )
    return items


def _dedupe(items: list[MediaItem]) -> list[MediaItem]:
    seen: set[str] = set()
    out = []
    for item in items:
        key = item.jellyfin_id or item.tmdb_id or item.imdb_id or f"{item.title}|{item.year}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _filename_for(item: MediaItem) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in item.title.lower()).strip("-")
    suffix = item.jellyfin_id or item.tmdb_id or item.imdb_id or uuid.uuid4().hex[:8]
    return f"{slug[:40]}-{suffix}.jpg"


def _artwork_urls(item: MediaItem) -> list[str]:
    """Backdrop first; poster fills in when Jellyfin has no wide art."""
    seen: set[str] = set()
    urls: list[str] = []
    for url in (item.backdrop_url, item.poster_url):
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _origin(url: str) -> str:
    """scheme://host[:port] — used so API keys are not sent to lookalike hosts.

    ``url.startswith(jellyfin_base)`` treated ``http://jf:8096.evil.example`` as
    the Jellyfin server and attached the MediaBrowser token.
    """
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _headers_for_url(url: str) -> dict[str, str] | None:
    settings = load_settings()
    jf = settings.jellyfin or {}
    base = (jf.get("url") or "").rstrip("/")
    key = jf.get("api_key") or ""
    if base and key and _origin(url) == _origin(base):
        return JellyfinProvider(url=base, api_key=key, user_id=jf.get("user_id") or "").auth_headers()
    return None


def _looks_like_image(data: bytes) -> bool:
    return looks_like_image(data)


def _default_http_get(url: str) -> bytes:
    data = HttpClient(timeout=30.0).get_bytes(url, headers=_headers_for_url(url))
    if not _looks_like_image(data):
        raise ValueError(f"Not an image: {url}")
    return data


def _logo_urls(item: MediaItem) -> list[str]:
    urls: list[str] = []
    for url in (item.logo_url,):
        if url and url not in urls and url.startswith(("http://", "https://")):
            urls.append(url)
    return urls


def _fetch_logo(item: MediaItem, http_get=None) -> bytes | None:
    bundled = logo_bytes_for_item(item)
    if bundled:
        return bundled
    getter = http_get or _default_http_get
    for url in _logo_urls(item):
        try:
            data = getter(url)
        except Exception:
            continue
        if data and looks_like_image(data):
            return data
    # Jellyfin Logo URLs often 404 for Seerr-only / TMDB ids — still try TMDB.
    tmdb_url = _tmdb_logo_url(item)
    if tmdb_url:
        try:
            data = getter(tmdb_url)
        except Exception:
            return None
        if data and looks_like_image(data):
            return data
    return None


def _tmdb_logo_url(item: MediaItem) -> str | None:
    """Resolve a TMDB clearlogo CDN URL when we have an API key + tmdb_id.

    Skip only when ``logo_url`` is already a TMDB CDN link (``_logo_urls`` will
    download it). Broken Jellyfin Logo guesses must not block this fallback —
    Seerr editor previews pass a TMDB id as ``item_id`` and used to invent a
    fake ``/Items/{tmdb}/Images/Logo`` URL that then short-circuited TMDB.
    """
    if item.logo_url and "image.tmdb.org" in item.logo_url:
        return None
    settings = load_settings()
    tm = settings.tmdb or {}
    key = (tm.get("api_key") or "").strip()
    if not key or not item.tmdb_id:
        return None
    try:
        return TmdbProvider(api_key=key, language=tm.get("language") or "en-US").fetch_logo_url(
            str(item.tmdb_id), item.media_type
        )
    except Exception:
        return None


def resolve_logo_bytes(
    item_id: str,
    tmdb_id: str | None = None,
    media_type: str = "movie",
    http_get=None,
) -> bytes | None:
    """Demo fixture, then Jellyfin Logo, then TMDB logos. Never raises."""
    from app.demo_art import logo_bytes

    try:
        bundled = logo_bytes(item_id) or (logo_bytes(tmdb_id) if tmdb_id else None)
        if bundled:
            return bundled
        kind = "tv" if media_type == "tv" else "movie"
        settings = load_settings()
        jf = settings.jellyfin or {}
        base = (jf.get("url") or "").rstrip("/")
        key = (jf.get("api_key") or "").strip()
        resolved_tmdb = (tmdb_id or "").strip() or None
        if not resolved_tmdb and item_id and str(item_id).isdigit():
            resolved_tmdb = str(item_id)
        # Numeric TMDB ids must not invent a Jellyfin Logo URL (Seerr editor).
        use_jellyfin = bool(base and key and item_id)
        if use_jellyfin and resolved_tmdb and str(item_id) == str(resolved_tmdb) and str(item_id).isdigit():
            use_jellyfin = False
        logo_url = f"{base}/Items/{item_id}/Images/Logo" if use_jellyfin else None
        item = MediaItem(
            title="",
            media_type=kind,
            jellyfin_id=item_id if use_jellyfin else None,
            tmdb_id=resolved_tmdb,
            logo_url=logo_url,
            source="jellyfin" if logo_url else "tmdb",
        )
        return _fetch_logo(item, http_get=http_get)
    except Exception:
        return None


def _fetch_artwork(item: MediaItem, http_get=None) -> bytes | None:
    getter = http_get or _default_http_get
    for url in _artwork_urls(item):
        try:
            data = getter(url)
        except Exception:
            continue
        if data and looks_like_image(data):
            return data
    local = still_path_for_item(item)
    if local and local.is_file():
        return local.read_bytes()
    return None


def _item_from_record(rec) -> MediaItem:
    return MediaItem(
        title=rec.title,
        year=rec.year,
        overview=rec.overview,
        rating=rec.rating,
        genres=rec.genres,
        official_rating=rec.official_rating,
        watch_state=rec.watch_state,
        source=rec.source,
        jellyfin_id=rec.jellyfin_id,
        tmdb_id=rec.tmdb_id,
        imdb_id=rec.imdb_id,
        action_url=rec.action_url,
    )


def _hydrate_item_art_urls(item: MediaItem) -> MediaItem:
    """Fill Jellyfin / demo artwork URLs so a later bake can recover the plate.

    Never treat the composited JPEG as backdrop art — that burns title text into
    the moving layer.
    """
    from app.demo_art import attach_demo_art

    settings = load_settings()
    jf = settings.jellyfin or {}
    base = (jf.get("url") or "").rstrip("/")
    key = jf.get("api_key") or ""
    updates: dict = {}
    if base and key and item.jellyfin_id:
        jf_id = item.jellyfin_id
        if not item.backdrop_url:
            updates["backdrop_url"] = f"{base}/Items/{jf_id}/Images/Backdrop?maxWidth=1920"
        if not item.poster_url:
            updates["poster_url"] = f"{base}/Items/{jf_id}/Images/Primary?maxHeight=1080"
        if not item.logo_url:
            updates["logo_url"] = f"{base}/Items/{jf_id}/Images/Logo"
    if updates:
        item = item.model_copy(update=updates)
    return attach_demo_art(item)


def generate_one(
    item: MediaItem,
    layout_name: str,
    motion: bool | None = None,
    replace: bool = False,
    http_get=None,
) -> WallpaperRecord | None:
    layout = load_layout(layout_name)
    if layout is None:
        raise ValueError(f"Unknown layout: {layout_name}")
    item = _hydrate_item_art_urls(item)
    catalog = catalog_store.load_catalog()
    previous = matching_records(catalog, item, layout_name)
    keep_pinned = any(rec.pinned for rec in previous)
    keep_hidden = any(rec.hidden for rec in previous)
    backdrop_bytes = _fetch_artwork(item, http_get=http_get)
    logo_bytes = _fetch_logo(item, http_get=http_get)
    settings = load_settings()
    from app.overlays import apply_overlays

    image = apply_overlays(render_still(item, layout, backdrop_bytes=backdrop_bytes, logo_bytes=logo_bytes), settings)
    filename = _filename_for(item)
    dest: Path = catalog_store.layout_dir(layout_name) / filename
    save_jpeg(image, dest)
    # Drop matching catalog rows only after the new JPEG is on disk. Deleting
    # first meant a render/fetch failure wiped the previous still. ``replace``
    # is kept as a caller flag; skip_existing=False used to duplicate rows for
    # the same title, so we always replace the previous catalog entries.
    if previous:
        catalog_store.remove_records({rec.id for rec in previous}, keep_files={dest.name})
    want_motion = settings.motion_wallpapers if motion is None else motion
    if not want_motion:
        # Status serves a sibling MP4 when it exists, ignoring catalog.has_video.
        # A still-only replace must not leave a stale baked loop on disk.
        dest.with_suffix(".mp4").unlink(missing_ok=True)
        dest.with_name(dest.stem + "_plate.jpg").unlink(missing_ok=True)
        dest.with_name(dest.stem + "_chrome.png").unlink(missing_ok=True)
    video = False
    style = None
    if want_motion:
        profile = profile_for_wallpaper(
            settings,
            jellyfin_id=item.jellyfin_id,
            tmdb_id=item.tmdb_id,
            imdb_id=item.imdb_id,
            filename=filename,
            title=item.title,
        )
        plate_path = dest.with_name(dest.stem + "_plate.jpg")
        chrome_path = dest.with_name(dest.stem + "_chrome.png")
        save_jpeg(render_plate(item, layout, backdrop_bytes=backdrop_bytes), plate_path)
        save_png(apply_overlays(render_chrome(item, layout, logo_bytes=logo_bytes), settings), chrome_path)
        ok, _ = generate_motion(
            dest,
            profile=profile,
            force=True,
            plate=plate_path,
            chrome=chrome_path,
        )
        plate_path.unlink(missing_ok=True)
        chrome_path.unlink(missing_ok=True)
        video = ok and has_motion(dest)
        if video:
            style = profile.normalized_style()
    record = WallpaperRecord(
        id=uuid.uuid4().hex,
        layout=layout_name,
        filename=filename,
        title=item.title,
        year=item.year,
        rating=item.rating,
        genres=item.genres,
        official_rating=item.official_rating,
        watch_state=item.watch_state,
        library_state=item.library_state,
        availability=item.availability,
        source=item.source,
        jellyfin_id=item.jellyfin_id,
        tmdb_id=item.tmdb_id,
        imdb_id=item.imdb_id,
        action_url=item.action_url,
        overview=item.overview,
        mtime=time.time(),
        has_video=video,
        parallax_style=style,
        pinned=keep_pinned,
        hidden=keep_hidden,
    )
    catalog_store.upsert(record)
    return record


def run_generate(request: GenerateRequest, http_get=None, job_id: str | None = None) -> dict:
    from app.progress import is_cancelled, report

    warnings: list[str] = []
    failed: list[str] = []
    pull = request.limit
    if request.ids:
        pull = max(request.limit, 200)
    report(job_id, status="running", message="Collecting titles…", current="Collecting titles")
    items = collect_items(request.source, pull, warnings=warnings, seerr_category=request.seerr_category)
    if request.ids:
        wanted = {i.lower() for i in request.ids}
        items = [
            item
            for item in items
            if (item.jellyfin_id or "").lower() in wanted
            or (item.tmdb_id or "").lower() in wanted
            or (item.imdb_id or "").lower() in wanted
        ]
    if request.skip_ids:
        banned = {i.lower() for i in request.skip_ids}
        items = [item for item in items if not (media_ids_of(item) & banned)]
    catalog = catalog_store.load_catalog()
    created: list[str] = []
    skipped: list[str] = []
    replaced: list[str] = []
    refreshed: list[str] = []
    total = max(len(items), 1)
    cancelled = False
    report(job_id, total=total, done=0, current=items[0].title if items else None, message="Generating stills…")
    for index, item in enumerate(items, start=1):
        if is_cancelled(job_id):
            cancelled = True
            break
        report(job_id, current=item.title, done=index - 1, total=total, message="Generating stills…")
        matches = matching_records(catalog, item, request.layout)
        skip_mode = request.skip_existing and not request.replace_existing
        if should_skip(
            catalog,
            item,
            request.layout,
            skip_mode,
            refresh_status=bool(request.refresh_status),
        ):
            skipped.append(item.title)
            report(job_id, done=index, skipped=skipped)
            continue
        replace = bool(request.replace_existing)
        if matches and request.replace_existing:
            replaced.append(item.title)
            replace = True
        elif matches and request.refresh_status and any(status_changed(rec, item) for rec in matches):
            refreshed.append(item.title)
            replace = True
        try:
            record = generate_one(
                item,
                request.layout,
                motion=request.motion,
                replace=replace,
                http_get=http_get,
            )
        except ValueError:
            raise
        except Exception as exc:
            failed.append(item.title)
            warnings.append(f"{item.title}: could not render ({exc})")
            report(job_id, done=index, failed=failed)
            continue
        if record:
            created.append(record.title)
            catalog = catalog_store.load_catalog()
        report(job_id, done=index, created=created, failed=failed, skipped=skipped)
    cleaned: list[str] = []
    if request.cleanup and not cancelled:
        doomed = records_to_cleanup(catalog_store.load_catalog(), items, request.layout)
        cleaned = [rec.title for rec in doomed]
        catalog_store.remove_records({rec.id for rec in doomed})
    done = len(created) + len(skipped) + len(failed)
    result = {
        "created": created,
        "skipped": skipped,
        "replaced": replaced,
        "refreshed": refreshed,
        "cleaned": cleaned,
        "failed": failed,
        "warnings": warnings,
        "count": len(created),
        "total": total,
        "done": done if cancelled else (total if items else 0),
        "cancelled": cancelled,
    }
    if cancelled:
        result["message"] = (
            f"Cancelled after {len(created)} still"
            f"{'' if len(created) == 1 else 's'}."
            if created
            else "Cancelled."
        )
    else:
        result["message"] = generate_message(request.layout, result)
    report(job_id, done=result["done"], total=total, current=None, message=result["message"])
    return result


def bake_motion(layout: str, filename: str | None = None, job_id: str | None = None) -> dict:
    """Bake ffmpeg VIDEO for one still (filename) or every still in a layout."""
    from app.overlays import apply_overlays
    from app.progress import is_cancelled, report

    settings = load_settings()
    base_profile = profile_from_settings(settings)
    wanted = (filename or "").strip().lower()
    if wanted.endswith(".mp4"):
        wanted = Path(wanted).with_suffix(".jpg").name.lower()
    elif wanted:
        wanted = Path(wanted).name.lower()
    targets = []
    for rec in catalog_store.load_catalog():
        if rec.layout.lower() != layout.lower():
            continue
        if wanted:
            rec_name = rec.filename.lower()
            rec_stem = Path(rec.filename).stem.lower()
            want_stem = Path(wanted).stem.lower()
            if rec_name != wanted and rec_stem != want_stem and wanted not in rec_name and want_stem not in rec_stem:
                continue
        targets.append(rec)
    done: list[str] = []
    failed: list[str] = []
    scanned = len(targets)
    total = max(scanned, 1)
    cancelled = False
    report(job_id, total=total, done=0, message="Baking motion…", current=targets[0].title if targets else None)
    for index, rec in enumerate(targets, start=1):
        if is_cancelled(job_id):
            cancelled = True
            break
        report(job_id, current=rec.title, done=index - 1, total=total, message="Baking motion…")
        jpg = catalog_store.wallpaper_file(rec.layout, rec.filename)
        if not jpg:
            failed.append(rec.filename)
            report(job_id, done=index, failed=failed)
            continue
        item = _hydrate_item_art_urls(_item_from_record(rec))
        layout_obj = load_layout(rec.layout)
        plate = chrome = None
        if layout_obj:
            artwork = _fetch_artwork(item)
            plate = jpg.with_name(jpg.stem + "_plate.jpg")
            chrome = jpg.with_name(jpg.stem + "_chrome.png")
            # Artwork plate only — never the text-burned JPEG.
            save_jpeg(render_plate(item, layout_obj, backdrop_bytes=artwork), plate)
            save_png(apply_overlays(render_chrome(item, layout_obj, logo_bytes=_fetch_logo(item)), settings), chrome)
        profile = profile_for_wallpaper(
            settings,
            jellyfin_id=rec.jellyfin_id,
            tmdb_id=rec.tmdb_id,
            imdb_id=rec.imdb_id,
            filename=rec.filename,
            title=rec.title,
        )
        ok, _ = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
        if plate:
            plate.unlink(missing_ok=True)
        if chrome:
            chrome.unlink(missing_ok=True)
        if ok:
            rec.has_video = True
            rec.parallax_style = profile.normalized_style()
            catalog_store.upsert(rec)
            done.append(rec.filename)
        else:
            failed.append(rec.filename)
        report(job_id, done=index, created=done, failed=failed)
    result = {
        "status": "cancelled" if cancelled else "ok",
        "generated": done,
        "failed": failed,
        "scanned": scanned,
        "style": base_profile.normalized_style(),
        "preset": settings.motion_preset,
        "duration": base_profile.duration,
        "vary": bool(getattr(settings, "motion_vary", True)),
        "count": len(done),
        "total": scanned,
        "done": len(done) + len(failed) if cancelled else scanned,
        "cancelled": cancelled,
        "layered": True,
        "chrome_locked": True,
    }
    result["message"] = motion_bake_message(layout, result)
    report(
        job_id,
        done=result["done"],
        total=total,
        current=None,
        message=result["message"],
        created=done,
        failed=failed,
    )
    return result


def seed_demo_catalog(layout: str = "Netflix Hero", limit: int = 6) -> dict:
    """First-boot demo seed.

    Titles are generated last-to-first so ``sort=latest`` is the first demo
    title (Northlight), matching VERIFY.md.
    """
    items = list(reversed(collect_items("demo", limit)))
    created: list[str] = []
    for item in items:
        record = generate_one(item, layout, motion=False, replace=False)
        if record:
            created.append(record.title)
    return {"created": created, "count": len(created)}
