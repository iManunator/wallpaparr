from __future__ import annotations

import time

from app.models import Layout, LayoutBackground, MediaItem
from app.progress import reset_for_tests
from app.render import render_chrome


def _wait_job(client, job_id: str, *, ticks: int = 80) -> dict:
    body = {}
    for _ in range(ticks):
        body = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] in {"done", "error", "cancelled"}:
            return body
        time.sleep(0.05)
    return body


def test_job_cancel_stops_generate(client, monkeypatch):
    reset_for_tests()
    from app.models import MediaItem

    items = [
        MediaItem(title=f"Title {i}", jellyfin_id=f"jf-{i}", media_type="movie")
        for i in range(8)
    ]

    def slow_one(item, layout, motion=False, replace=False, http_get=None):
        # Give the cancel request time to land between titles.
        time.sleep(0.08)
        from app import catalog as catalog_store
        from app.models import WallpaperRecord

        rec = WallpaperRecord(
            id=f"id-{item.jellyfin_id}",
            title=item.title,
            layout=layout,
            filename=f"{item.jellyfin_id}.jpg",
            jellyfin_id=item.jellyfin_id,
        )
        catalog_store.upsert(rec)
        return rec

    monkeypatch.setattr("app.generate.collect_items", lambda *a, **k: items)
    monkeypatch.setattr("app.generate.generate_one", slow_one)

    started = client.post(
        "/api/jobs",
        json={"kind": "generate", "layout": "Netflix Hero", "source": "demo", "limit": 8, "skip_existing": False},
    ).json()
    assert started["status"] in {"queued", "running"}
    job_id = started["id"]

    for _ in range(40):
        snap = client.get(f"/api/jobs/{job_id}").json()
        if snap["status"] == "running" and snap["done"] >= 1:
            break
        time.sleep(0.05)

    cancelled = client.post(f"/api/jobs/{job_id}/cancel").json()
    assert cancelled["cancel_requested"] is True
    assert cancelled["message"] == "Cancelling…"

    final = _wait_job(client, job_id, ticks=120)
    assert final["status"] == "cancelled"
    assert final["result"]["cancelled"] is True
    assert len(final["created"]) < 8
    assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 404


def test_gallery_delete_removes_still_video_and_catalog(client, suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    gallery = suite_dirs["gallery"]
    rec = next(r for r in catalog_mod.load_catalog() if r.has_video)
    jpg = gallery / rec.layout / rec.filename
    mp4 = jpg.with_suffix(".mp4")
    plate = jpg.with_name(jpg.stem + "_plate.jpg")
    chrome = jpg.with_name(jpg.stem + "_chrome.png")
    plate.write_bytes(b"plate")
    chrome.write_bytes(b"chrome")
    assert jpg.is_file() and mp4.is_file()

    out = client.delete(f"/api/gallery/{rec.id}").json()
    assert rec.id in out["deleted"]
    assert rec.title in out["titles"]
    assert out["count"] == 1
    assert not jpg.exists()
    assert not mp4.exists()
    assert not plate.exists()
    assert not chrome.exists()
    leftover = client.get("/api/gallery").json()
    assert all(item["id"] != rec.id for item in leftover)


def test_gallery_delete_post_and_bulk(client, suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    records = catalog_mod.load_catalog()
    first, second = records[0], records[1]
    one = client.post(f"/api/gallery/delete/{first.id}").json()
    assert first.id in one["deleted"]
    bulk = client.post("/api/gallery/delete", json={"ids": [second.id, "missing-id"]}).json()
    assert second.id in bulk["deleted"]
    assert "missing-id" in bulk["missing"]
    assert client.delete("/api/gallery/missing-id").status_code == 404
    assert client.post("/api/gallery/delete", json={"ids": []}).status_code == 400


def test_gallery_delete_missing_file_drops_catalog_row(client, suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    rec = catalog_mod.load_catalog()[0]
    jpg = suite_dirs["gallery"] / rec.layout / rec.filename
    jpg.unlink()
    out = client.delete(f"/api/gallery/{rec.id}").json()
    assert rec.id in out["deleted"]
    leftover = client.get("/api/gallery").json()
    assert all(item["id"] != rec.id for item in leftover)


def test_gallery_delete_all_skips_pins_by_default(client, suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    pinned = next(r for r in catalog_mod.load_catalog() if r.title == "Northlight")
    client.post(f"/api/gallery/{pinned.id}/flag", json={"pinned": True})
    before = client.get("/api/gallery").json()
    assert len(before) == 6
    out = client.post("/api/gallery/delete-all", json={}).json()
    assert out["status"] == "ok"
    assert pinned.id not in out["deleted"]
    assert pinned.id in out["skipped_pinned"]
    assert out["pinned_kept"] == 1
    assert out["include_pins"] is False
    assert out["count"] == 5
    assert "Kept 1 pinned wallpaper" in out["message"]
    leftover = client.get("/api/gallery").json()
    assert [item["id"] for item in leftover] == [pinned.id]
    status = client.get("/api/wallpaper/status", params={"layout": "Netflix Hero", "pool": "pinned"}).json()
    assert status["title"] == "Northlight"
    assert status["imageUrl"]
    assert status["path"]


def test_gallery_delete_all_including_pins(client):
    pinned = next(item for item in client.get("/api/gallery").json() if item["title"] == "Harbor Season")
    client.post(f"/api/gallery/{pinned['id']}/flag", json={"pinned": True})
    out = client.post("/api/gallery/delete-all", json={"include_pins": True}).json()
    assert out["count"] == 6
    assert out["include_pins"] is True
    assert out["pinned_kept"] == 0
    assert pinned["id"] in out["deleted"]
    assert client.get("/api/gallery").json() == []
    status = client.get("/api/wallpaper/status", params={"layout": "Netflix Hero"}).json()
    assert status["imageUrl"] is None
    assert status.get("path") in {None, ""}


def test_gallery_delete_all_empty_and_pins_only(client):
    wiped = client.post("/api/gallery/delete-all", json={"include_pins": True}).json()
    assert wiped["count"] == 6
    assert client.get("/api/gallery").json() == []
    empty = client.post("/api/gallery/delete-all", json={}).json()
    assert empty["count"] == 0
    assert empty["message"] == "Gallery is already empty."
    again = client.post("/api/gallery/delete-all", json={"include_pins": True}).json()
    assert again["message"] == "Gallery is already empty."
    seed = client.post(
        "/api/generate",
        json={
            "layout": "Netflix Hero",
            "source": "demo",
            "limit": 1,
            "skip_existing": False,
            "ids": ["demo-jf-1"],
        },
    )
    assert seed.status_code == 200
    rec = client.get("/api/gallery").json()[0]
    client.post(f"/api/gallery/{rec['id']}/flag", json={"pinned": True})
    kept = client.post("/api/gallery/delete-all", json={}).json()
    assert kept["count"] == 0
    assert kept["pinned_kept"] == 1
    assert "Nothing else to delete" in kept["message"]
    assert client.get("/api/gallery").json()[0]["id"] == rec["id"]


def test_gallery_delete_all_layout_filter_and_bulk_all_alias(client):
    north = next(item for item in client.get("/api/gallery").json() if item["title"] == "Northlight")
    client.post(f"/api/gallery/{north['id']}/flag", json={"pinned": True})
    scoped = client.post("/api/gallery/delete-all", json={"layout": "Netflix Hero"}).json()
    assert scoped["count"] == 2
    leftover = client.get("/api/gallery").json()
    titles = {item["title"] for item in leftover}
    assert "Northlight" in titles
    assert "Harbor Season" not in titles
    assert "Glass Orchard" not in titles
    alias = client.post("/api/gallery/delete", json={"all": True, "include_pins": True}).json()
    assert alias["count"] == len(leftover)
    assert client.get("/api/gallery").json() == []


def test_jobs_generate_reports_progress(client):
    reset_for_tests()
    start = client.post(
        "/api/jobs",
        json={
            "kind": "generate",
            "layout": "Netflix Hero",
            "source": "demo",
            "limit": 1,
            "skip_existing": False,
            "replace_existing": True,
            "ids": ["demo-jf-1"],
            "motion": False,
        },
    )
    assert start.status_code == 200
    job = start.json()
    assert job["id"]
    assert job["kind"] == "generate"
    assert job["status"] in {"queued", "running", "done"}
    body = _wait_job(client, job["id"], ticks=200)
    assert body["status"] == "done", body
    assert body["percent"] == 100
    assert body["total"] >= 1
    assert body["result"]["count"] == 1
    latest = client.get("/api/jobs/latest").json()
    assert latest["id"] == job["id"]


def test_jobs_latest_idle_and_unknown_kind(client):
    reset_for_tests()
    idle = client.get("/api/jobs/latest").json()
    assert idle["status"] == "idle"
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.post("/api/jobs", json={"kind": "explode"}).status_code == 400


def test_jobs_conflict_when_running(client, monkeypatch):
    from app import progress

    fake = progress.JobState(id="busy", kind="generate", status="running")
    monkeypatch.setattr(progress, "running_job", lambda: fake)
    res = client.post("/api/jobs", json={"kind": "cron", "layout": "Netflix Hero", "source": "demo", "limit": 1})
    assert res.status_code == 409


def test_jobs_motion_kind(client, monkeypatch):
    reset_for_tests()

    def fake_bake(layout, filename=None, job_id=None):
        from app.progress import report

        report(job_id, total=1, done=0, current="Night Relay", message="Baking motion…")
        report(job_id, done=1, created=["relay.jpg"], current="Night Relay")
        return {
            "status": "ok",
            "generated": ["relay.jpg"],
            "count": 1,
            "total": 1,
            "done": 1,
            "layered": True,
            "chrome_locked": True,
            "message": "Baked parallax VIDEO for relay.jpg.",
        }

    monkeypatch.setattr("app.api.bake_motion", fake_bake)
    start = client.post(
        "/api/jobs",
        json={"kind": "motion", "layout": "Prime Cinematic", "path": "relay.jpg"},
    )
    assert start.status_code == 200
    job = start.json()
    body = _wait_job(client, job["id"])
    assert body["status"] == "done", body
    assert body["current"] in (None, "Night Relay")
    assert body["result"]["layered"] is True
    assert body["result"]["chrome_locked"] is True
    assert body["percent"] == 100


def test_watch_badge_injected_and_hideable():
    layout = Layout(
        name="Bare",
        canvas_width=1920,
        canvas_height=1080,
        background=LayoutBackground(
            fade_left=0,
            fade_right=0,
            fade_top=0,
            fade_bottom=0,
            vignette=0,
            overlay_opacity=0,
            gradient_opacity=0,
        ),
        layers=[],
        show_watch_badge=True,
    )
    watched = MediaItem(title="Probe", year=2024, watch_state="unwatched")
    blank = MediaItem(title="Probe", year=2024, watch_state="")
    with_badge = render_chrome(watched, layout)
    without = render_chrome(blank, layout)
    assert with_badge.tobytes() != without.tobytes()
    hidden = layout.model_copy(update={"show_watch_badge": False})
    assert render_chrome(watched, hidden).tobytes() == without.tobytes()


def test_seerr_badge_injected_next_to_watch_and_hideable():
    layout = Layout(
        name="Bare",
        canvas_width=1920,
        canvas_height=1080,
        background=LayoutBackground(
            fade_left=0,
            fade_right=0,
            fade_top=0,
            fade_bottom=0,
            vignette=0,
            overlay_opacity=0,
            gradient_opacity=0,
        ),
        layers=[],
        show_watch_badge=True,
        show_seerr_badge=True,
    )
    seerr_only = MediaItem(
        title="Probe",
        year=2024,
        watch_state="unwatched",
        library_state="seerr_only",
        availability="requestable",
        source="jellyseerr",
    )
    library = MediaItem(
        title="Probe",
        year=2024,
        watch_state="unwatched",
        library_state="in_library",
        availability="available",
        source="jellyfin",
    )
    blank = MediaItem(title="Probe", year=2024)
    with_seerr = render_chrome(seerr_only, layout)
    library_only = render_chrome(library, layout)
    empty = render_chrome(blank, layout)
    assert with_seerr.tobytes() != library_only.tobytes()
    assert library_only.tobytes() != empty.tobytes()
    hidden = layout.model_copy(update={"show_seerr_badge": False})
    assert render_chrome(seerr_only, hidden).tobytes() == library_only.tobytes()
    both_hidden = layout.model_copy(update={"show_watch_badge": False, "show_seerr_badge": False})
    assert render_chrome(seerr_only, both_hidden).tobytes() == empty.tobytes()
