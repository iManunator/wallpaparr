from app.messages import enrich_provider_result, generate_message, motion_bake_message, provider_test_message


def test_jellyfin_success_and_failure_copy():
    assert provider_test_message("jellyfin", {"ok": True, "server": "Living Room"}) == "Connected to Jellyfin (Living Room)"
    assert provider_test_message("jellyfin", {"ok": False, "error": "connection refused"}).startswith(
        "Could not reach Jellyfin:"
    )
    assert "API key are required" in provider_test_message(
        "jellyfin", {"ok": False, "error": "Jellyfin URL and API key are required"}
    )


def test_seerr_tmdb_demo_copy():
    assert provider_test_message("jellyseerr", {"ok": True, "server": "1.9.0"}) == "Connected to Jellyseerr / Seerr (version 1.9.0)"
    assert provider_test_message("tmdb", {"ok": True, "server": "TMDB"}) == "Connected to TMDB"
    assert "license-safe" in provider_test_message("demo", {"ok": True, "server": "Demo catalog"})
    body = enrich_provider_result("jellyfin", {"ok": True, "server": "Box"})
    assert body["message"] == "Connected to Jellyfin (Box)"
    assert body["provider"] == "jellyfin"


def test_generate_message_counts():
    msg = generate_message(
        "Netflix Hero",
        {"created": ["A", "B"], "skipped": ["C"], "replaced": [], "cleaned": [], "failed": [], "warnings": []},
    )
    assert "Created 2 stills for Netflix Hero" in msg
    assert "(A, B)" in msg
    assert "skipped 1" in msg
    empty = generate_message("Prime Cinematic", {"created": [], "skipped": ["A", "B"], "warnings": ["Jellyfin is not configured. Using the demo catalog."]})
    assert empty.startswith("No new stills")
    assert "Jellyfin is not configured" in empty


def test_motion_bake_message():
    one = motion_bake_message(
        "Netflix Hero",
        {"generated": ["northlight.jpg"], "style": "parallax", "preset": "bold", "duration": 10},
    )
    assert "northlight.jpg" in one
    assert "bold" in one
    empty = motion_bake_message("Prime Cinematic", {"generated": [], "failed": []})
    assert empty.startswith("No VIDEO clips")
