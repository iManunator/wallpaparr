"""Projectivy wallpaper HTTP API + editor/gallery/settings routes."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response

from app import catalog as catalog_store
from app.config import (
    is_redacted_api_key,
    load_settings,
    merge_provider_secrets,
    public_base_url,
    redact_settings_dump,
    save_settings,
)
from app.demo_art import public_catalog, still_bytes as demo_still_bytes
from app.generate import bake_motion, collect_items, run_generate
from app.images import image_media_type, looks_like_image
from app.messages import enrich_provider_result
from app.providers import HttpClient
from app.jobs import invalid_cron_jobs, reload_jobs, run_now
from app.layouts import delete_layout, list_layouts, load_layout, reset_layout, save_layout, seed_presets
from app import __version__
from app.models import AppSettings, GenerateRequest, Layout, WallpaperStatus
from app.seerr_status import seerr_kind
from app.motion import intensity_from_preset, profile_from_settings, wallpaper_motion_seed
from app.ops import load_ops
from app.providers.demo import DemoProvider
from app.providers.jellyfin import JellyfinProvider
from app.providers.seerr import SeerrProvider
from app.providers.tmdb import TmdbProvider
from app.queues import QUEUE_DEFS, TASTE_PRESETS, queue_ids_for, summarize_queues
from app.selection import SelectionQuery, select_wallpaper, unique_values

router = APIRouter()

_MEDIA_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _safe_media_id(value: str | None) -> str | None:
    """Reject path characters so artwork/logo proxy IDs cannot traverse Jellyfin URLs."""
    text = str(value or "").strip()
    if not text or _MEDIA_ID.fullmatch(text) is None:
        return None
    return text


def _int_or_none(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float_or_none(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _public_url(request: Request, layout: str, filename: str) -> str:
    settings = load_settings()
    base = public_base_url(settings)
    # Prefer configured public URL; fall back to the incoming request host.
    if not base or "127.0.0.1" in base or "localhost" in base:
        base = str(request.base_url).rstrip("/")
    encoded_layout = quote(layout, safe="")
    encoded_file = quote(filename)
    return f"{base}/api/wallpaper/image/{encoded_layout}/{encoded_file}"


@router.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "wallpaparr", "version": __version__}


@router.get("/api/layouts/list")
def layouts_list() -> list[str]:
    seed_presets()
    return list_layouts()


@router.get("/api/layouts/with-images")
def layouts_with_images() -> list[str]:
    names = catalog_store.layouts_with_images()
    return names


@router.get("/api/layouts")
def layouts_detail() -> list[dict[str, Any]]:
    seed_presets()
    out = []
    for name in list_layouts():
        layout = load_layout(name)
        if layout:
            out.append(layout.model_dump())
    return out


@router.get("/api/layouts/load/{name:path}")
def layouts_load(name: str) -> dict[str, Any]:
    layout = load_layout(name)
    if not layout:
        raise HTTPException(404, "Layout not found")
    return layout.model_dump()


@router.post("/api/layouts/save")
def layouts_save(layout: Layout) -> dict[str, Any]:
    try:
        saved = save_layout(layout)
    except ValueError:
        raise HTTPException(400, "Invalid layout name")
    return {"status": "ok", "layout": saved.model_dump()}


@router.post("/api/layouts/reset/{name:path}")
def layouts_reset(name: str) -> dict[str, Any]:
    reset = reset_layout(name)
    if not reset:
        raise HTTPException(400, "Not a bundled preset — nothing to reset to")
    return {"status": "ok", "layout": reset.model_dump()}


@router.post("/api/layouts/delete/{name:path}")
def layouts_delete(name: str) -> dict[str, Any]:
    try:
        deleted = delete_layout(name)
    except ValueError:
        raise HTTPException(400, "Invalid layout name")
    if not deleted:
        raise HTTPException(400, "Cannot delete a bundled preset (save a copy first)")
    return {"status": "ok"}


@router.get("/api/options")
def suite_options() -> dict[str, Any]:
    return {
        "sort": ["random", "latest", "oldest", "rating", "rating_asc", "year", "year_asc"],
        "pools": [
            "unwatched",
            "partial",
            "watched",
            "in_library",
            "seerr_only",
            "requestable",
            "available",
            "upcoming",
            "pinned",
            "source:jellyfin",
            "source:jellyseerr",
            "source:plex",
        ],
        "seerr_categories": [
            {"id": "trending", "label": "Trending"},
            {"id": "movies_popular", "label": "Popular movies"},
            {"id": "tv_popular", "label": "Popular series"},
            {"id": "movies_upcoming", "label": "Upcoming movies"},
            {"id": "tv_upcoming", "label": "Upcoming series"},
        ],
        "motion_styles": ["parallax", "kenburns", "drift"],
        "motion_qualities": ["light", "standard", "cinematic"],
        "motion_presets": ["subtle", "balanced", "cinematic", "bold"],
        "gradient_types": ["linear", "radial"],
        "title_displays": ["auto", "logo", "text"],
        "taste_profiles": list(TASTE_PRESETS.keys()),
        "queues": [{"id": qid, "label": spec["label"]} for qid, spec in QUEUE_DEFS.items()],
        "pick_modes": [
            "random",
            "latest",
            "oldest",
            "rating_high",
            "rating_low",
            "year_new",
            "year_old",
            "unwatched",
            "partial",
            "watched",
            "in_library",
            "seerr_only",
            "requestable",
            "available_seerr",
            "source_jellyfin",
            "source_seerr",
            "source_plex",
            "recent_years",
            "high_rated",
            "alt_random_latest",
            "alt_library_unwatched",
            "alt_library_seerr",
            "alt_two_layouts",
            "mix_weighted",
            "layout_round_robin",
            "genre_round_robin",
            "no_repeat_bag",
            "tonight",
            "continue_watching",
            "newly_added",
            "seerr_trending",
            "pinned",
        ],
        "clients": [
            {"name": "Moonfin", "package": "org.moonfin.androidtv", "type": "deep_link"},
            {"name": "Jellyfin", "package": "org.jellyfin.androidtv", "type": "deep_link"},
            {"name": "SeerrTV", "package": "ca.devmesh.seerrtv", "type": "launch"},
            {"name": "Fladder", "package": "nl.jknaapen.fladder", "type": "launch"},
            {"name": "Kodi", "package": "org.xbmc.kodi", "type": "launch"},
            {"name": "Wholphin", "package": "com.github.damontecres.wholphin", "type": "launch"},
            {"name": "Void", "package": "com.hritwik.avoid", "type": "launch"},
        ],
    }


@router.get("/api/genres/list")
def genres_list() -> list[str]:
    return unique_values(catalog_store.load_catalog(), "genres")


@router.get("/api/ages/list")
def ages_list() -> list[str]:
    return unique_values(catalog_store.load_catalog(), "official_rating")


@router.get("/api/year/list")
def year_list() -> list[str]:
    years = unique_values(catalog_store.load_catalog(), "year")
    return sorted(years, reverse=True)


@router.get("/api/wallpaper/status", response_model=WallpaperStatus)
def wallpaper_status(
    request: Request,
    layout: str = Query("Default"),
    genre: str | None = None,
    age_rating: str | None = Query(None),
    age: str | None = None,
    min_year: str | None = None,
    max_year: str | None = None,
    min_rating: str | None = None,
    max_rating: str | None = None,
    sort: str = "random",
    pool: str | None = None,
    exclude: str | None = None,
    exclude_path: str | None = None,
    queue: str | None = None,
    profile: str | None = None,
) -> WallpaperStatus:
    catalog = catalog_store.load_catalog()
    settings = load_settings()
    pool_arg = pool
    sort_arg = sort or "random"
    profile_arg = profile
    taste_weights = None
    if queue:
        spec = QUEUE_DEFS.get(queue)
        if spec:
            pool_arg = spec.get("pool") or pool_arg
            if spec.get("sort") and sort_arg == "random":
                sort_arg = str(spec["sort"])
    active_profile = (settings.taste_profile or "tonight").strip().lower()
    if (pool_arg or "").startswith("taste:"):
        requested = pool_arg.split(":", 1)[1].strip().lower()
        pool_arg = None
        # Plugin "Tonight's mix" sends pool=taste:tonight. Treat that as the
        # configured mix so the TV matches the web Tonight page + sliders.
        if not profile_arg:
            profile_arg = active_profile if requested in ("tonight", active_profile) else requested
    if profile_arg:
        name = str(profile_arg).strip().lower()
        if name == active_profile:
            taste_weights = settings.taste_weights
    query = SelectionQuery(
        layout=layout,
        genre=genre,
        age_rating=age_rating or age,
        min_year=_int_or_none(min_year),
        max_year=_int_or_none(max_year),
        min_rating=_float_or_none(min_rating),
        max_rating=_float_or_none(max_rating),
        sort=sort_arg,
        pool=pool_arg,
        exclude=exclude or exclude_path,
        profile=profile_arg,
        taste_weights=taste_weights,
    )
    selected = select_wallpaper(catalog, query)
    status = WallpaperStatus(sort=query.sort, pool=query.pool or queue or None, layout=layout)
    if not selected:
        return status
    return _fill_status(request, status, selected, settings)


def _fill_status(request: Request, status: WallpaperStatus, selected, settings) -> WallpaperStatus:
    jpg = catalog_store.wallpaper_file(selected.layout, selected.filename)
    if not jpg:
        return status
    status.layout = selected.layout
    status.imageUrl = _public_url(request, selected.layout, selected.filename)
    status.actionUrl = selected.action_url
    status.title = selected.title
    status.path = selected.filename
    status.pinned = bool(selected.pinned)
    queues = queue_ids_for(selected)
    status.queue = queues[0] if queues else None
    status.watchState = selected.watch_state or None
    status.libraryState = selected.library_state or None
    status.availability = selected.availability or None
    status.seerrStatus = seerr_kind(selected.library_state, selected.availability, selected.source)
    status.source = selected.source or None
    mp4 = jpg.with_suffix(".mp4")
    has_clip = mp4.is_file() and mp4.stat().st_size > 1000
    if has_clip:
        status.videoUrl = _public_url(request, selected.layout, mp4.name)
        status.mediaType = "video"
        status.parallaxStyle = selected.parallax_style or settings.motion_style
        profile = profile_from_settings(settings)
        status.motionDuration = profile.duration
    else:
        status.mediaType = "image"
        status.videoUrl = None
    return status


@router.get("/api/wallpaper/image/{layout}/{filename:path}")
def wallpaper_image(layout: str, filename: str):
    path = catalog_store.wallpaper_file(layout, filename)
    if not path:
        raise HTTPException(404, "File not found")
    media = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "video/mp4"
    return FileResponse(path, media_type=media)


@router.get("/api/gallery")
def gallery(layout: str | None = None) -> list[dict[str, Any]]:
    records = catalog_store.load_catalog()
    if layout:
        records = [r for r in records if r.layout.lower() == layout.lower()]
    records.sort(key=lambda r: r.mtime, reverse=True)
    return [r.model_dump() for r in records]


@router.post("/api/gallery/delete-all")
def gallery_delete_all(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    include_pins = _truthy(body.get("include_pins", body.get("includePins")))
    layout = body.get("layout")
    layout_name = str(layout).strip() if layout else None
    out = catalog_store.delete_all(include_pins=include_pins, layout=layout_name)
    return _gallery_delete_result(out, include_pins=include_pins, all_mode=True)


@router.post("/api/gallery/delete")
def gallery_delete_bulk(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    if body.get("all") is True or str(body.get("all") or "").lower() in {"1", "true", "yes"}:
        return gallery_delete_all(body)
    ids = body.get("ids") or body.get("id") or []
    if isinstance(ids, str):
        ids = [ids]
    wanted = {str(item) for item in ids if item}
    if not wanted:
        raise HTTPException(400, "Pass ids to delete")
    out = catalog_store.delete_records(wanted)
    if not out["deleted"]:
        raise HTTPException(404, "Not found")
    return _gallery_delete_result(out)


@router.post("/api/gallery/delete/{record_id}")
def gallery_delete(record_id: str) -> dict[str, Any]:
    return _gallery_delete_one(record_id)


@router.delete("/api/gallery/{record_id}")
def gallery_delete_rest(record_id: str) -> dict[str, Any]:
    return _gallery_delete_one(record_id)


def _gallery_delete_one(record_id: str) -> dict[str, Any]:
    out = catalog_store.delete_records({record_id})
    if not out["deleted"]:
        raise HTTPException(404, "Not found")
    return _gallery_delete_result(out)


def _gallery_delete_result(
    out: dict[str, Any],
    *,
    include_pins: bool = False,
    all_mode: bool = False,
) -> dict[str, Any]:
    skipped = list(out.get("skipped_pinned") or [])
    titles = list(out.get("titles") or [])
    return {
        "status": "ok",
        "deleted": out.get("deleted") or [],
        "files": out.get("files") or [],
        "titles": titles,
        "missing": out.get("missing") or [],
        "errors": out.get("errors") or [],
        "skipped_pinned": skipped,
        "skipped_titles": out.get("skipped_titles") or [],
        "count": len(out.get("deleted") or []),
        "pinned_kept": len(skipped),
        "include_pins": include_pins,
        "message": (
            _delete_all_message(titles, skipped, include_pins)
            if all_mode
            else _delete_message(titles)
        ),
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _delete_message(titles: list[str]) -> str:
    if not titles:
        return "Deleted 0 wallpapers."
    if len(titles) == 1:
        return f"Deleted “{titles[0]}”."
    return f"Deleted {len(titles)} wallpapers."


def _delete_all_message(titles: list[str], skipped_pinned: list[str], include_pins: bool) -> str:
    if not titles and not skipped_pinned:
        return "Gallery is already empty."
    if not titles and skipped_pinned:
        n = len(skipped_pinned)
        noun = "wallpaper" if n == 1 else "wallpapers"
        return f"Kept {n} pinned {noun}. Nothing else to delete."
    msg = _delete_message(titles)
    if skipped_pinned and not include_pins:
        n = len(skipped_pinned)
        noun = "wallpaper" if n == 1 else "wallpapers"
        msg += f" Kept {n} pinned {noun}."
    return msg


@router.post("/api/gallery/{record_id}/flag")
def gallery_flag(record_id: str, body: dict[str, Any]) -> dict[str, Any]:
    catalog = catalog_store.load_catalog()
    rec = next((r for r in catalog if r.id == record_id), None)
    if not rec:
        raise HTTPException(404, "Not found")
    if "pinned" in body:
        rec.pinned = bool(body["pinned"])
    if "hidden" in body:
        rec.hidden = bool(body["hidden"])
    catalog_store.upsert(rec)
    return {"status": "ok", "record": rec.model_dump()}


@router.get("/api/queues")
def list_queues(layout: str | None = None) -> list[dict[str, Any]]:
    views = summarize_queues(catalog_store.load_catalog(), layout)
    return [{"id": v.id, "label": v.label, "count": v.count, "titles": v.titles} for v in views]


@router.get("/api/tonight")
def tonight(
    request: Request,
    layout: str | None = Query(None),
    exclude: str | None = None,
) -> dict[str, Any]:
    settings = load_settings()
    catalog = catalog_store.load_catalog()
    status = wallpaper_status(
        request,
        layout=layout,
        profile=settings.taste_profile or "tonight",
        exclude=exclude,
    )
    queues = list_queues(layout)
    selected_id = None
    artwork_url = None
    path = status.path
    rec = None
    if path:
        rec = next(
            (r for r in catalog if (not layout or r.layout.lower() == layout.lower()) and r.filename == path),
            None,
        )
        if rec is None:
            rec = next((r for r in catalog if r.filename == path), None)
        if rec:
            selected_id = rec.jellyfin_id or rec.tmdb_id or rec.imdb_id
            if rec.jellyfin_id or rec.tmdb_id:
                artwork_url = f"/api/media/artwork/{quote(str(rec.jellyfin_id or rec.tmdb_id), safe='')}"
    motion_seed = wallpaper_motion_seed(
        jellyfin_id=rec.jellyfin_id if rec else None,
        tmdb_id=rec.tmdb_id if rec else None,
        imdb_id=rec.imdb_id if rec else None,
        filename=rec.filename if rec else path,
        title=rec.title if rec else status.title,
    )
    return {
        "status": status.model_dump(),
        "queues": queues,
        "profile": settings.taste_profile,
        "motion": {
            "style": settings.motion_style,
            "preset": settings.motion_preset,
            "intensity": intensity_from_preset(settings.motion_preset),
            "duration": settings.motion_duration,
            "light_leak": settings.light_leak,
            "vary": bool(settings.motion_vary),
            "seed": motion_seed,
        },
        "preview": {
            "artworkUrl": artwork_url,
            "itemId": selected_id,
            "layered": True,
        },
    }


@router.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    settings = load_settings()
    catalog = catalog_store.load_catalog()
    ops = load_ops()
    jf = settings.jellyfin or {}
    se = settings.jellyseerr or {}
    tm = settings.tmdb or {}
    return {
        "ok": True,
        "service": "wallpaparr",
        "version": __version__,
        "gallery": {
            "count": len(catalog),
            "layouts": sorted({r.layout for r in catalog}),
            "videos": sum(1 for r in catalog if r.has_video),
            "pinned": sum(1 for r in catalog if r.pinned),
            "hidden": sum(1 for r in catalog if r.hidden),
        },
        "cron": {
            "jobs": len(settings.cron_jobs or []),
            "last": ops.get("cron"),
            "last_generate": ops.get("generate"),
            "errors": invalid_cron_jobs(settings.cron_jobs, enabled_only=True),
        },
        "providers": {
            "jellyfin": {
                "configured": bool(jf.get("url") and jf.get("api_key")),
                "last_test": ops.get("test_jellyfin"),
            },
            "jellyseerr": {
                "configured": bool(se.get("url") and se.get("api_key")),
                "last_test": ops.get("test_jellyseerr") or ops.get("test_seerr"),
            },
            "tmdb": {"configured": bool(tm.get("api_key")), "last_test": ops.get("test_tmdb")},
            "demo": {"configured": True, "last_test": ops.get("test_demo")},
        },
        "motion": {
            "style": settings.motion_style,
            "preset": settings.motion_preset,
            "quality": settings.motion_quality,
            "light_leak": settings.light_leak,
            "vary": bool(settings.motion_vary),
        },
        "taste": {"profile": settings.taste_profile, "weights": settings.taste_weights},
    }


@router.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return redact_settings_dump(load_settings().model_dump())


@router.post("/api/settings")
def post_settings(settings: AppSettings) -> dict[str, Any]:
    stored = load_settings()
    merged = merge_provider_secrets(settings, stored)
    cron_errors = invalid_cron_jobs(merged.cron_jobs, enabled_only=True)
    if cron_errors:
        names = ", ".join(f"{row['name']} ({row['cron']})" for row in cron_errors)
        raise HTTPException(
            400,
            f"Invalid cron expression on enabled job(s): {names}",
        )
    save_settings(merged)
    reload_jobs()
    return {"status": "ok", "settings": redact_settings_dump(merged.model_dump())}


@router.post("/api/settings/test/{provider}")
def test_provider(provider: str, body: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    """Test a provider. Optional JSON body overrides saved URL/api_key so Settings can Test before Save."""
    settings = load_settings()
    key = provider.lower()
    from app.ops import record_event

    draft = body if isinstance(body, dict) else {}
    overrides = {
        k: v
        for k, v in draft.items()
        if v is not None and str(v).strip() != "" and not (k == "api_key" and is_redacted_api_key(v))
    }

    result: dict[str, Any]
    if key == "jellyfin":
        cfg = {**(settings.jellyfin or {}), **overrides}
        result = JellyfinProvider(url=cfg.get("url") or "", api_key=cfg.get("api_key") or "", user_id=cfg.get("user_id") or "").test()
    elif key in ("seerr", "jellyseerr"):
        cfg = {**(settings.jellyseerr or {}), **overrides}
        result = SeerrProvider(url=cfg.get("url") or "", api_key=cfg.get("api_key") or "").test()
    elif key == "tmdb":
        cfg = {**(settings.tmdb or {}), **overrides}
        result = TmdbProvider(api_key=cfg.get("api_key") or "").test()
    elif key == "demo":
        result = DemoProvider().test()
    else:
        raise HTTPException(404, "Unknown provider")
    record_event(f"test_{key}", {"ok": bool(result.get("ok")), "provider": key})
    return enrich_provider_result(key, result)


@router.get("/api/media")
def media_preview(source: str = "demo", limit: int = Query(12, ge=1, le=40)) -> list[dict[str, Any]]:
    return [item.model_dump() for item in collect_items(source, limit)]


@router.get("/api/demo/catalog")
def demo_catalog() -> dict[str, Any]:
    return public_catalog()


@router.get("/api/demo/attribution")
def demo_attribution():
    from pathlib import Path as AttrPath

    path = AttrPath(__file__).resolve().parent / "demo_stills" / "ATTRIBUTION.md"
    if not path.is_file():
        raise HTTPException(404, "Attribution file missing")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@router.get("/api/media/logo/{item_id}")
def media_logo(item_id: str, tmdb_id: str | None = None, media_type: str = "movie"):
    """Clearlogo proxy: demo PNG, Jellyfin Logo, or TMDB logos. Rejects non-images."""
    from app.generate import resolve_logo_bytes

    item_id = _safe_media_id(item_id)
    tmdb_id = _safe_media_id(tmdb_id) if tmdb_id else None
    if not item_id:
        raise HTTPException(404, "No logo for this title")
    data = resolve_logo_bytes(item_id, tmdb_id=tmdb_id, media_type=media_type)
    if data and looks_like_image(data):
        return Response(
            content=data,
            media_type=image_media_type(data),
            headers={"Cache-Control": "public, max-age=300"},
        )
    raise HTTPException(404, "No logo for this title")


@router.get("/api/media/artwork/{item_id}")
def media_artwork(item_id: str, kind: str = Query("backdrop")):
    """Same-origin artwork for the editor: demo stills, then Jellyfin Backdrop/Primary."""
    item_id = _safe_media_id(item_id)
    if not item_id:
        raise HTTPException(404, "No image")
    bundled = demo_still_bytes(item_id)
    if bundled and looks_like_image(bundled):
        return Response(
            content=bundled,
            media_type=image_media_type(bundled),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    settings = load_settings()
    jf = settings.jellyfin or {}
    base = (jf.get("url") or "").rstrip("/")
    key = jf.get("api_key") or ""
    if not base or not key:
        raise HTTPException(404, "Jellyfin is not configured")
    headers = JellyfinProvider(url=base, api_key=key, user_id=jf.get("user_id") or "").auth_headers()
    kinds = ["Primary", "Backdrop"] if kind == "poster" else ["Backdrop", "Primary"]
    last_error = "No image"
    for image_kind in kinds:
        query = "maxWidth=1920" if image_kind == "Backdrop" else "maxHeight=1080"
        url = f"{base}/Items/{item_id}/Images/{image_kind}?{query}"
        try:
            data = HttpClient(timeout=20.0).get_bytes(url, headers=headers)
        except Exception as exc:
            last_error = str(exc)
            continue
        if data and looks_like_image(data):
            return Response(
                content=data,
                media_type=image_media_type(data),
                headers={"Cache-Control": "private, max-age=60"},
            )
        if data:
            last_error = "Jellyfin did not return an image"
    raise HTTPException(404, last_error)


@router.post("/api/generate")
def generate(request: GenerateRequest) -> dict[str, Any]:
    from app.ops import record_event

    try:
        result = run_generate(request)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        record_event("generate", {"ok": False, "error": str(exc)})
        raise HTTPException(500, f"Generate failed: {exc}") from exc
    record_event(
        "generate",
        {"layout": request.layout, "count": result.get("count"), "ok": True, "warnings": result.get("warnings")},
    )
    return result


@router.get("/api/jobs/latest")
def jobs_latest() -> dict[str, Any]:
    from app.progress import idle_snapshot, latest_job

    job = latest_job()
    return job.as_dict() if job else idle_snapshot()


@router.get("/api/jobs/{job_id}")
def jobs_get(job_id: str) -> dict[str, Any]:
    from app.progress import get_job

    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.as_dict()


@router.post("/api/jobs/{job_id}/cancel")
def jobs_cancel(job_id: str) -> dict[str, Any]:
    from app.progress import request_cancel

    job = request_cancel(job_id)
    if not job:
        raise HTTPException(404, "Job not found or not running")
    return job.as_dict()


@router.post("/api/jobs")
def jobs_start(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    from app.ops import record_event
    from app.progress import spawn

    kind = str(body.get("kind") or "generate").strip().lower()
    try:
        if kind == "generate":
            payload = {key: body[key] for key in GenerateRequest.model_fields if key in body}
            request = GenerateRequest(**payload)

            def worker(job_id: str) -> dict[str, Any]:
                result = run_generate(request, job_id=job_id)
                record_event(
                    "generate",
                    {"layout": request.layout, "count": result.get("count"), "ok": True, "warnings": result.get("warnings")},
                )
                return result

            job = spawn("generate", worker, message="Generating stills…")
        elif kind in ("motion", "generate-motion"):
            layout = str(body.get("layout") or "Netflix Hero")
            path = body.get("path")

            def worker(job_id: str) -> dict[str, Any]:
                result = bake_motion(layout, filename=path, job_id=job_id)
                record_event(
                    "generate",
                    {"layout": layout, "count": result.get("count"), "ok": True, "motion": True, "path": path},
                )
                return result

            job = spawn("motion", worker, message="Baking motion…")
        elif kind == "cron":
            spec = {key: value for key, value in body.items() if key != "kind"}

            def worker(job_id: str) -> dict[str, Any]:
                return run_now(spec, job_id=job_id)

            job = spawn("cron", worker, message="Running scheduled generate…")
        else:
            raise HTTPException(400, f"Unknown job kind: {kind}")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return job.as_dict()


@router.post("/api/wallpaper/generate-motion")
def generate_motion_batch(layout: str = "Netflix Hero", path: str | None = None) -> dict[str, Any]:
    from app.ops import record_event

    result = bake_motion(layout, filename=path)
    record_event(
        "generate",
        {"layout": layout, "count": result.get("count"), "ok": True, "motion": True, "path": path},
    )
    return result


@router.post("/api/cron/run")
def cron_run(body: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    try:
        return run_now(body or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Cron run failed: {exc}") from exc
