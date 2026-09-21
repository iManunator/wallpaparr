from __future__ import annotations


def test_demo_seed_latest_is_northlight(suite_dirs):
    from app.catalog import load_catalog
    from app.generate import seed_demo_catalog
    from app.selection import SelectionQuery, select_wallpaper

    result = seed_demo_catalog(layout="Netflix Hero", limit=6)
    assert result["count"] == 6
    assert result["created"][-1] == "Northlight"
    picked = select_wallpaper(load_catalog(), SelectionQuery(layout="Netflix Hero", sort="latest"))
    assert picked is not None
    assert picked.title == "Northlight"
