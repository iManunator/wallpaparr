from __future__ import annotations


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["service"] == "wallpaparr"
    assert body["version"] == "1.2.7"


def test_layouts_list_includes_presets(client):
    names = client.get("/api/layouts/list").json()
    assert "Netflix Hero" in names
    assert "Prime Cinematic" in names
    assert "Google TV Clean" in names
    assert "Projectivy Dock" in names
    assert "Status Focus" in names
    assert "Jellyfin Dense" in names


def test_layouts_with_images_only_generated(client):
    names = client.get("/api/layouts/with-images").json()
    assert set(names) == {"Netflix Hero", "Prime Cinematic"}


def test_genres_ages_years_lists(client):
    genres = client.get("/api/genres/list").json()
    ages = client.get("/api/ages/list").json()
    years = client.get("/api/year/list").json()
    assert "Sci-Fi" in genres
    assert "PG-13" in ages
    assert "2024" in years


def test_wallpaper_status_random_has_contract_fields(client):
    body = client.get("/api/wallpaper/status", params={"layout": "Netflix Hero", "sort": "latest"}).json()
    assert body["imageUrl"]
    assert body["imageUrl"].endswith("/northlight.jpg") or "northlight.jpg" in body["imageUrl"]
    assert body["title"] == "Northlight"
    assert body["path"] == "northlight.jpg"
    assert body["actionUrl"] == "jellyfin://items/demo-jf-1"
    assert body["mediaType"] in ("image", "video")
    assert body["sort"] == "latest"
    assert body["layout"] == "Netflix Hero"
    assert body["watchState"] == "unwatched"
    assert body["libraryState"] == "in_library"
    assert body["availability"] == "available"
    assert body["seerrStatus"] is None
    assert body["source"] == "jellyfin"


def test_wallpaper_status_genre_filter(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "genre": "Drama", "sort": "rating"},
    ).json()
    assert body["title"] in {"Harbor Season", "Glass Orchard"}


def test_wallpaper_status_pool_unwatched(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "pool": "unwatched", "sort": "random"},
    ).json()
    assert body["title"] == "Northlight"


def test_wallpaper_status_pool_seerr_only(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Prime Cinematic", "pool": "seerr_only"},
    ).json()
    assert body["title"] == "Signal Country"
    assert body["libraryState"] == "seerr_only"
    assert body["availability"] == "requestable"
    assert body["seerrStatus"] == "seerr_only"
    assert body["watchState"] == "unwatched"
    assert body["source"] == "jellyseerr"


def test_wallpaper_status_exclude(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "sort": "rating", "exclude": "northlight.jpg"},
    ).json()
    assert body["title"] != "Northlight"
    assert body["path"]


def test_wallpaper_status_year_and_rating_filters(client):
    body = client.get(
        "/api/wallpaper/status",
        params={
            "layout": "Prime Cinematic",
            "min_year": "2020",
            "max_year": "2025",
            "min_rating": "8.0",
            "sort": "rating",
        },
    ).json()
    assert body["title"] == "Night Relay"


def test_options_lists_pick_modes_and_motion(client):
    body = client.get("/api/options").json()
    assert "unwatched" in body["pools"]
    assert "pinned" in body["pools"]
    assert "parallax" in body["motion_styles"]
    assert "layout_round_robin" in body["pick_modes"]
    assert "tonight" in body["pick_modes"]
    assert "subtle" in body["motion_presets"]
    assert "linear" in body["gradient_types"]
    assert "auto" in body["title_displays"]
    assert "logo" in body["title_displays"]
    assert "cinephile" in body["taste_profiles"]


def test_wallpaper_status_video_includes_parallax_fields(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Prime Cinematic", "sort": "rating"},
    ).json()
    assert body["title"] == "Night Relay"
    assert body["mediaType"] == "video"
    assert body["videoUrl"]
    assert body["imageUrl"]
    assert body["parallaxStyle"] in {"parallax", "kenburns", "drift"}
    assert body["motionDuration"] >= 2


def test_wallpaper_status_missing_layout(client):
    body = client.get("/api/wallpaper/status", params={"layout": "Does Not Exist"}).json()
    assert body["imageUrl"] is None
    assert body["path"] is None


def test_wallpaper_image_served(client):
    response = client.get("/api/wallpaper/image/Netflix Hero/northlight.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_generate_demo_skip_and_replace(client):
    first = client.post(
        "/api/generate",
        json={"layout": "Google TV Clean", "source": "demo", "limit": 2, "skip_existing": False},
    ).json()
    assert first["count"] == 2
    skipped = client.post(
        "/api/generate",
        json={"layout": "Google TV Clean", "source": "demo", "limit": 2, "skip_existing": True},
    ).json()
    assert skipped["count"] == 0
    assert len(skipped["skipped"]) == 2
    replaced = client.post(
        "/api/generate",
        json={
            "layout": "Google TV Clean",
            "source": "demo",
            "limit": 2,
            "skip_existing": False,
            "replace_existing": True,
        },
    ).json()
    assert replaced["count"] == 2


def test_gallery_and_settings_roundtrip(client):
    gallery = client.get("/api/gallery", params={"layout": "Netflix Hero"}).json()
    assert len(gallery) == 3
    settings = client.get("/api/settings").json()
    assert settings["motion_vary"] is True
    settings["public_base_url"] = "http://tv.local:8787"
    saved = client.post("/api/settings", json=settings)
    assert saved.status_code == 200
    assert client.get("/api/settings").json()["public_base_url"] == "http://tv.local:8787"


def test_wallpaper_status_watched_pool(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "pool": "watched", "sort": "rating"},
    ).json()
    assert body["title"] == "Glass Orchard"


def test_generate_ids_and_skip_ids(client):
    only = client.post(
        "/api/generate",
        json={
            "layout": "Status Focus",
            "source": "demo",
            "limit": 20,
            "skip_existing": False,
            "ids": ["demo-jf-1"],
        },
    ).json()
    assert only["count"] == 1
    assert only["created"] == ["Northlight"]
    skipped = client.post(
        "/api/generate",
        json={
            "layout": "Status Focus",
            "source": "demo",
            "limit": 20,
            "skip_existing": False,
            "skip_ids": ["demo-jf-1", "90001", "tt9000001"],
            "ids": ["demo-jf-1"],
        },
    ).json()
    assert skipped["count"] == 0


def test_health_includes_version(client):
    body = client.get("/api/health").json()
    assert body["version"]


def test_settings_roundtrip_motion_options(client):
    settings = client.get("/api/settings").json()
    settings["motion_style"] = "parallax"
    settings["motion_intensity"] = 0.8
    settings["motion_duration"] = 7
    settings["editor_theme"] = "high-contrast"
    assert client.post("/api/settings", json=settings).status_code == 200
    saved = client.get("/api/settings").json()
    assert saved["motion_style"] == "parallax"
    assert saved["motion_intensity"] == 0.8
    assert saved["editor_theme"] == "high-contrast"
    settings["motion_preset"] = "bold"
    settings["light_leak"] = False
    settings["taste_profile"] = "cinephile"
    settings["overlays_enabled"] = False
    settings["overlay_clock"] = True
    assert client.post("/api/settings", json=settings).status_code == 200
    saved = client.get("/api/settings").json()
    assert saved["motion_preset"] == "bold"
    assert saved["light_leak"] is False
    assert saved["taste_profile"] == "cinephile"
    assert saved["overlays_enabled"] is False
    settings["motion_vary"] = False
    assert client.post("/api/settings", json=settings).status_code == 200
    saved = client.get("/api/settings").json()
    assert saved["motion_vary"] is False
    settings["motion_vary"] = True
    assert client.post("/api/settings", json=settings).status_code == 200
    assert client.get("/api/settings").json()["motion_vary"] is True
    settings["title_display"] = "logo"
    assert client.post("/api/settings", json=settings).status_code == 200
    assert client.get("/api/settings").json()["title_display"] == "logo"


def test_dashboard_and_tonight(client):
    dash = client.get("/api/dashboard").json()
    assert dash["ok"] is True
    assert dash["service"] == "wallpaparr"
    assert dash["gallery"]["count"] == 6
    assert dash["providers"]["demo"]["configured"] is True
    assert dash["taste"]["profile"]
    tonight = client.get("/api/tonight", params={"layout": "Netflix Hero"}).json()
    assert tonight["status"]["imageUrl"]
    assert tonight["status"]["title"]
    assert tonight["profile"]
    assert tonight["motion"]["vary"] is True
    assert tonight["motion"]["seed"]
    assert tonight["preview"]["layered"] is True
    assert tonight["preview"]["itemId"]
    assert tonight["preview"]["artworkUrl"]
    ids = {q["id"] for q in tonight["queues"]}
    assert "unwatched" in ids
    assert "continue_watching" in ids


def test_tonight_without_layout_spans_the_whole_catalog(client):
    """Omitting layout should consider every layout's wallpapers, not just one —
    otherwise a baked VIDEO sitting under a different layout never surfaces."""
    any_layout = client.get("/api/tonight").json()
    scoped = client.get("/api/tonight", params={"layout": "Netflix Hero"}).json()
    any_counts = {q["id"]: q["count"] for q in any_layout["queues"]}
    scoped_counts = {q["id"]: q["count"] for q in scoped["queues"]}
    assert any_counts["unwatched"] > scoped_counts["unwatched"]
    assert any_layout["status"]["layout"] in {"Netflix Hero", "Prime Cinematic"}


def test_gallery_pin_and_never_show(client):
    gallery = client.get("/api/gallery", params={"layout": "Netflix Hero"}).json()
    rec = next(item for item in gallery if item["title"] == "Glass Orchard")
    pinned = client.post(f"/api/gallery/{rec['id']}/flag", json={"pinned": True}).json()
    assert pinned["record"]["pinned"] is True
    status = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "pool": "pinned"},
    ).json()
    assert status["title"] == "Glass Orchard"
    assert status["pinned"] is True
    hidden = client.post(f"/api/gallery/{rec['id']}/flag", json={"hidden": True, "pinned": False}).json()
    assert hidden["record"]["hidden"] is True
    again = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "pool": "pinned"},
    ).json()
    assert again["imageUrl"] is None


def test_wallpaper_status_taste_and_queue(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "profile": "tonight"},
    ).json()
    assert body["imageUrl"]
    queued = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "queue": "continue_watching"},
    ).json()
    assert queued["title"] == "Harbor Season"
    trending = client.get(
        "/api/wallpaper/status",
        params={"layout": "Prime Cinematic", "queue": "seerr_trending", "sort": "rating"},
    ).json()
    assert trending["title"] in {"Signal Country", "Night Relay"}


def test_provider_test_records_ops(client):
    body = client.post("/api/settings/test/demo").json()
    assert body["ok"] is True
    dash = client.get("/api/dashboard").json()
    assert dash["providers"]["demo"]["last_test"]["ok"] is True


def test_generate_with_clock_overlay(client):
    settings = client.get("/api/settings").json()
    settings["overlays_enabled"] = True
    settings["overlay_clock"] = True
    assert client.post("/api/settings", json=settings).status_code == 200
    out = client.post(
        "/api/generate",
        json={
            "layout": "Projectivy Dock",
            "source": "demo",
            "limit": 1,
            "skip_existing": False,
            "ids": ["demo-jf-1"],
        },
    ).json()
    assert out["count"] == 1
    gallery = client.get("/api/gallery", params={"layout": "Projectivy Dock"}).json()
    assert gallery[0]["title"] == "Northlight"


def test_stale_has_video_flag_does_not_advertise_missing_mp4(client, suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    records = catalog_mod.load_catalog()
    north = next(r for r in records if r.title == "Northlight")
    north.has_video = True
    north.parallax_style = "parallax"
    catalog_mod.upsert(north)
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "sort": "latest"},
    ).json()
    assert body["title"] == "Northlight"
    assert body["imageUrl"]
    assert body["videoUrl"] is None
    assert body["mediaType"] == "image"


def test_replace_preserves_pin_and_hidden(client):
    gallery = client.get("/api/gallery", params={"layout": "Netflix Hero"}).json()
    rec = next(item for item in gallery if item["title"] == "Northlight")
    client.post(f"/api/gallery/{rec['id']}/flag", json={"pinned": True})
    out = client.post(
        "/api/generate",
        json={
            "layout": "Netflix Hero",
            "source": "demo",
            "limit": 20,
            "skip_existing": False,
            "replace_existing": True,
            "ids": ["demo-jf-1"],
        },
    ).json()
    assert out["count"] == 1
    gallery = client.get("/api/gallery", params={"layout": "Netflix Hero"}).json()
    north = next(item for item in gallery if item["title"] == "Northlight")
    assert north["pinned"] is True


def test_wallpaper_status_taste_pool_prefix(client):
    body = client.get(
        "/api/wallpaper/status",
        params={"layout": "Netflix Hero", "pool": "taste:tonight"},
    ).json()
    assert body["imageUrl"]
    assert body["title"]


def test_generate_motion_batch_contract(client):
    body = client.post("/api/wallpaper/generate-motion", params={"layout": "Prime Cinematic"}).json()
    assert body["status"] == "ok"
    assert "generated" in body
    assert body["style"] in {"parallax", "kenburns", "drift"}
    assert body["layered"] is True
    assert body["chrome_locked"] is True
    assert "message" in body


def test_generate_motion_single_path_contract(client):
    body = client.post(
        "/api/wallpaper/generate-motion",
        params={"layout": "Netflix Hero", "path": "northlight.jpg"},
    ).json()
    assert body["status"] == "ok"
    assert body["scanned"] == 1
    assert body["count"] in {0, 1}
    if body["generated"]:
        assert any("northlight" in name for name in body["generated"])


def test_cron_run_now(client):
    body = client.post(
        "/api/cron/run",
        json={
            "layout": "Google TV Clean",
            "source": "demo",
            "limit": 1,
            "skip_existing": False,
            "ids": ["demo-jf-1"],
        },
    ).json()
    assert body["count"] == 1
    assert "Created" in body["message"]


def test_media_artwork_requires_jellyfin(client):
    assert client.get("/api/media/artwork/abc").status_code == 404


def test_media_artwork_serves_demo_still(client):
    response = client.get("/api/media/artwork/demo-jf-1")
    assert response.status_code == 200
    assert response.content[:3] == b"\xff\xd8\xff"
    assert response.headers["content-type"].startswith("image/")
    assert len(response.content) > 20_000


def test_demo_catalog_lists_licenses(client):
    body = client.get("/api/demo/catalog").json()
    assert body["count"] == 6
    licenses = {row["license"] for row in body["items"]}
    assert "Public domain" in licenses
    assert any(row["title"] == "Northlight" for row in body["items"])
    north = next(row for row in body["items"] if row["title"] == "Northlight")
    assert north["logo_url"]
    assert north["title_fallback"] == "logo"
    harbor = next(row for row in body["items"] if row["title"] == "Harbor Season")
    assert harbor["logo_url"] in (None, "")
    assert harbor["title_fallback"] == "text"
    attr = client.get("/api/demo/attribution")
    assert attr.status_code == 200
    assert b"CC BY-SA 3.0" in attr.content
    assert b"Diliff" in attr.content


def test_media_artwork_rejects_html(client, monkeypatch):
    from app.config import save_settings
    from app.models import AppSettings

    save_settings(AppSettings(jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"}))

    class FakeHttp:
        def __init__(self, timeout: float = 15.0):
            self.timeout = timeout

        def get_bytes(self, url, headers=None):
            return b"<!DOCTYPE html><title>login</title>"

    monkeypatch.setattr("app.api.HttpClient", FakeHttp)
    response = client.get("/api/media/artwork/not-a-demo")
    assert response.status_code == 404


def test_generate_returns_message(client):
    out = client.post(
        "/api/generate",
        json={"layout": "Google TV Clean", "source": "demo", "limit": 8, "skip_existing": False, "ids": ["demo-jf-2"]},
    ).json()
    assert out["count"] == 1
    assert "Harbor Season" in out["message"]


def test_provider_test_includes_message(client):
    body = client.post("/api/settings/test/demo").json()
    assert body["ok"] is True
    assert "Demo catalog ready" in body["message"]


def test_media_artwork_proxies_jellyfin_bytes(client, monkeypatch):
    from app.config import save_settings
    from app.models import AppSettings

    save_settings(AppSettings(jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"}))

    class FakeHttp:
        def __init__(self, timeout: float = 15.0):
            self.timeout = timeout

        def get_bytes(self, url, headers=None):
            assert "Backdrop" in url or "Primary" in url
            assert headers and "secret" in headers["Authorization"]
            return b"\xff\xd8\xffFAKE"

    monkeypatch.setattr("app.api.HttpClient", FakeHttp)
    response = client.get("/api/media/artwork/abc")
    assert response.status_code == 200
    assert response.content.startswith(b"\xff\xd8\xff")


def test_media_logo_serves_demo_png(client):
    response = client.get("/api/media/logo/demo-jf-1")
    assert response.status_code == 200
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert response.headers["content-type"].startswith("image/png")


def test_media_logo_missing_demo_falls_back_to_404(client):
    assert client.get("/api/media/logo/demo-jf-2").status_code == 404


def test_media_logo_rejects_non_image(client, monkeypatch):
    from app.config import save_settings
    from app.models import AppSettings

    save_settings(AppSettings(jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"}))

    class FakeHttp:
        def __init__(self, timeout: float = 15.0):
            self.timeout = timeout

        def get_bytes(self, url, headers=None):
            assert "/Images/Logo" in url
            return b"<!DOCTYPE html>nope"

    monkeypatch.setattr("app.generate.HttpClient", FakeHttp)
    assert client.get("/api/media/logo/abc123").status_code == 404


def test_media_logo_seerr_tmdb_id_uses_tmdb_not_fake_jellyfin(client, monkeypatch):
    """Editor passes Seerr TMDB ids — must not invent /Items/{tmdb}/Images/Logo."""
    from app.config import save_settings
    from app.models import AppSettings

    save_settings(
        AppSettings(
            jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"},
            tmdb={"api_key": "tmdb-secret", "language": "en-US"},
        )
    )
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    seen: list[str] = []

    class FakeHttp:
        def __init__(self, timeout: float = 15.0):
            self.timeout = timeout

        def get_json(self, url, headers=None, params=None):
            assert "/3/movie/550/images" in url
            return {"logos": [{"file_path": "/clear.png", "iso_639_1": "en", "vote_average": 9}]}

        def get_bytes(self, url, headers=None):
            seen.append(url)
            assert "image.tmdb.org" in url
            assert "/Items/" not in url
            return png

    monkeypatch.setattr("app.generate.HttpClient", FakeHttp)
    monkeypatch.setattr("app.providers.tmdb.HttpClient", FakeHttp)
    response = client.get("/api/media/logo/550?tmdb_id=550&media_type=movie")
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")
    assert seen and all("/Items/" not in u for u in seen)


def test_media_logo_proxies_jellyfin_logo(client, monkeypatch):
    from app.config import save_settings
    from app.models import AppSettings

    save_settings(AppSettings(jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"}))
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

    class FakeHttp:
        def __init__(self, timeout: float = 15.0):
            self.timeout = timeout

        def get_bytes(self, url, headers=None):
            assert url.endswith("/Items/abc/Images/Logo")
            assert headers and "secret" in headers["Authorization"]
            assert headers.get("X-Emby-Token") == "secret"
            return png

    monkeypatch.setattr("app.generate.HttpClient", FakeHttp)
    response = client.get("/api/media/logo/abc")
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")


def test_layout_json_includes_title_display(client):
    body = client.get("/api/layouts/load/Netflix Hero").json()
    assert body["title_display"] in {"auto", "logo", "text"}
    body["title_display"] = "logo"
    saved = client.post("/api/layouts/save", json=body)
    assert saved.status_code == 200
    again = client.get("/api/layouts/load/Netflix Hero").json()
    assert again["title_display"] == "logo"


def test_layouts_reset_restores_bundled_preset_dna(client):
    body = client.get("/api/layouts/load/Netflix Hero").json()
    original_title_x = next(layer["x"] for layer in body["layers"] if layer["slot"] == "title")
    body["title_display"] = "text"
    for layer in body["layers"]:
        if layer["slot"] == "title":
            layer["x"] = 999
    client.post("/api/layouts/save", json=body).raise_for_status()
    edited = client.get("/api/layouts/load/Netflix Hero").json()
    assert edited["title_display"] == "text"

    reset = client.post("/api/layouts/reset/Netflix Hero")
    assert reset.status_code == 200
    restored = client.get("/api/layouts/load/Netflix Hero").json()
    assert restored["title_display"] == "auto"
    restored_title_x = next(layer["x"] for layer in restored["layers"] if layer["slot"] == "title")
    assert restored_title_x == original_title_x == 80


def test_layouts_reset_rejects_custom_layout(client):
    custom = client.get("/api/layouts/load/Netflix Hero").json()
    custom["name"] = "My Custom Copy"
    custom["preset"] = False
    custom["preset_id"] = None
    client.post("/api/layouts/save", json=custom).raise_for_status()

    reset = client.post("/api/layouts/reset/My Custom Copy")
    assert reset.status_code == 400


def test_layouts_delete_removes_custom_layout(client):
    custom = client.get("/api/layouts/load/Netflix Hero").json()
    custom["name"] = "My Deletable Copy"
    custom["preset"] = False
    custom["preset_id"] = None
    client.post("/api/layouts/save", json=custom).raise_for_status()
    assert "My Deletable Copy" in client.get("/api/layouts/list").json()

    deleted = client.post("/api/layouts/delete/My Deletable Copy")
    assert deleted.status_code == 200
    assert "My Deletable Copy" not in client.get("/api/layouts/list").json()


def test_layouts_delete_rejects_bundled_preset(client):
    deleted = client.post("/api/layouts/delete/Netflix Hero")
    assert deleted.status_code == 400
    assert "Netflix Hero" in client.get("/api/layouts/list").json()
