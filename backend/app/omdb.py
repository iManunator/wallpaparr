"""OMDb enrichment: ratings, awards, and box office by IMDb id.

OMDb has no logo/image data — that still comes from TMDB (see
app/providers/tmdb.py and the Seerr detail fetch in app/providers/seerr.py).
This is purely the text-metadata side: Rotten Tomatoes / Metacritic /
combined IMDb rating, awards, and box office, matched to a MediaItem via its
imdb_id. Cached in-process since these fields rarely change after a title's
initial release.
"""

from __future__ import annotations

import time

from app.providers import HttpClient

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SEC = 24 * 60 * 60

OMDB_URL = "https://www.omdbapi.com/"


def _cache_get(imdb_id: str) -> dict | None:
    entry = _CACHE.get(imdb_id)
    if not entry:
        return None
    stamped, data = entry
    if time.time() - stamped > _CACHE_TTL_SEC:
        return None
    return data


def fetch_omdb_fields(imdb_id: str, api_key: str, client: HttpClient | None = None) -> dict:
    """Return the OMDb fields we map onto MediaItem, or {} on any failure."""
    imdb_id = (imdb_id or "").strip()
    api_key = (api_key or "").strip()
    if not imdb_id or not api_key:
        return {}
    cached = _cache_get(imdb_id)
    if cached is not None:
        return cached
    http = client or HttpClient(timeout=6.0)
    try:
        data = http.get_json(OMDB_URL, params={"i": imdb_id, "apikey": api_key, "plot": "full"})
    except Exception:
        return {}
    if not isinstance(data, dict) or data.get("Response") == "False":
        return {}

    fields: dict = {}
    for rating in data.get("Ratings") or []:
        source = rating.get("Source")
        value = str(rating.get("Value") or "")
        if source == "Rotten Tomatoes" and value.endswith("%"):
            try:
                fields["rotten_tomatoes"] = int(value.rstrip("%"))
            except ValueError:
                pass
        elif source == "Metacritic" and "/" in value:
            try:
                fields["metacritic"] = int(value.split("/")[0])
            except ValueError:
                pass
    imdb_rating = data.get("imdbRating")
    if imdb_rating and imdb_rating != "N/A":
        try:
            fields["imdb_rating"] = float(imdb_rating)
        except ValueError:
            pass
    if data.get("Awards") and data["Awards"] != "N/A":
        fields["awards"] = data["Awards"]
    if data.get("BoxOffice") and data["BoxOffice"] != "N/A":
        fields["box_office"] = data["BoxOffice"]

    _CACHE[imdb_id] = (time.time(), fields)
    return fields
