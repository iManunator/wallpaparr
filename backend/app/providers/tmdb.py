"""Optional TMDB enrichment (title search + images)."""

from __future__ import annotations

from app.models import MediaItem
from app.providers import HttpClient

TMDB_IMAGE = "https://image.tmdb.org/t/p"


def select_logo_path(payload: dict | None, language: str = "en-US") -> str | None:
    """Pick a TMDB clearlogo: prefer requested language, then null iso, then en; PNG + votes."""
    if not isinstance(payload, dict):
        return None
    logos = payload.get("logos") or []
    if not isinstance(logos, list):
        return None
    lang = (language or "en").split("-")[0].lower() or "en"

    def rank(entry: dict) -> tuple:
        path = str(entry.get("file_path") or "")
        iso = entry.get("iso_639_1")
        iso_n = (iso or "").lower() if isinstance(iso, str) else ""
        if iso_n == lang:
            lang_rank = 0
        elif iso is None or iso_n == "":
            lang_rank = 1
        elif iso_n == "en":
            lang_rank = 2
        else:
            lang_rank = 3
        png_rank = 0 if path.lower().endswith(".png") else 1
        vote = -float(entry.get("vote_average") or 0)
        return (lang_rank, png_rank, vote)

    ranked = [row for row in logos if isinstance(row, dict) and row.get("file_path")]
    if not ranked:
        return None
    ranked.sort(key=rank)
    return str(ranked[0]["file_path"])


def logo_image_url(path: str | None) -> str | None:
    if not path:
        return None
    suffix = path if str(path).startswith("/") else f"/{path}"
    return f"{TMDB_IMAGE}/original{suffix}"


class TmdbProvider:
    name = "tmdb"

    def __init__(self, api_key: str = "", language: str = "en-US", client: HttpClient | None = None):
        self.api_key = api_key or ""
        self.language = language or "en-US"
        self.client = client or HttpClient()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def test(self) -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "TMDB API key is required"}
        try:
            self.client.get_json(
                "https://api.themoviedb.org/3/configuration",
                params={"api_key": self.api_key},
            )
            return {"ok": True, "server": "TMDB"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def enrich(self, item: MediaItem) -> MediaItem:
        if not self.is_configured():
            return item
        try:
            kind = "tv" if item.media_type == "tv" else "movie"
            if item.tmdb_id:
                detail = self.client.get_json(
                    f"https://api.themoviedb.org/3/{kind}/{item.tmdb_id}",
                    params={"api_key": self.api_key, "language": self.language},
                )
            else:
                search = self.client.get_json(
                    f"https://api.themoviedb.org/3/search/{kind}",
                    params={"api_key": self.api_key, "query": item.title, "year": item.year or ""},
                )
                results = search.get("results") or []
                if not results:
                    return item
                detail = results[0]
            genres = [g["name"] if isinstance(g, dict) else str(g) for g in detail.get("genres") or []]
            backdrop = detail.get("backdrop_path")
            poster = detail.get("poster_path")
            date = str(detail.get("release_date") or detail.get("first_air_date") or "")
            year = int(date[:4]) if date[:4].isdigit() else None
            runtime = ""
            if kind == "movie" and detail.get("runtime"):
                minutes = int(detail["runtime"])
                hours, mins = divmod(minutes, 60)
                runtime = f"{hours}h {mins}m" if hours else f"{mins}m"
            elif kind == "tv":
                ep = detail.get("episode_run_time") or []
                if isinstance(ep, list) and ep:
                    runtime = f"{int(ep[0])}m"
            updates = {
                "overview": item.overview or detail.get("overview") or "",
                "rating": item.rating or float(detail.get("vote_average") or 0),
                "tmdb_id": item.tmdb_id or str(detail.get("id") or "") or None,
            }
            if genres and not item.genres:
                updates["genres"] = genres
            if year and not item.year:
                updates["year"] = year
            if runtime and not item.runtime:
                updates["runtime"] = runtime
            if backdrop and not item.backdrop_url:
                updates["backdrop_url"] = f"https://image.tmdb.org/t/p/w1280{backdrop}"
            if poster and not item.poster_url:
                updates["poster_url"] = f"{TMDB_IMAGE}/w500{poster}"
            tmdb_id = updates.get("tmdb_id") or item.tmdb_id
            if tmdb_id and not item.logo_url:
                logo = self.fetch_logo_url(str(tmdb_id), kind)
                if logo:
                    updates["logo_url"] = logo
            return item.model_copy(update=updates)
        except Exception:
            return item

    def fetch_logo_url(self, tmdb_id: str, media_type: str = "movie") -> str | None:
        if not self.is_configured() or not tmdb_id:
            return None
        kind = "tv" if media_type == "tv" else "movie"
        lang = (self.language or "en").split("-")[0]
        try:
            payload = self.client.get_json(
                f"https://api.themoviedb.org/3/{kind}/{tmdb_id}/images",
                params={
                    "api_key": self.api_key,
                    "include_image_language": f"{lang},null,en",
                },
            )
        except Exception:
            return None
        return logo_image_url(select_logo_path(payload if isinstance(payload, dict) else None, self.language))
