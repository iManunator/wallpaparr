"""Jellyfin library client (Movies / Series / Episodes)."""

from __future__ import annotations

from urllib.parse import urljoin

from app import __version__
from app.models import MediaItem
from app.providers import HttpClient

# Wallpaper titles: whole movies/series. BoxSets still slip through some servers.
_LIST_TYPES = "Movie,Series"
_PARSE_TYPES = frozenset({"Movie", "Series", "Season", "Episode"})


def _year_from_jellyfin(raw: dict) -> int | None:
    """ProductionYear first; PremiereDate / EndDate year as fallback."""
    year = raw.get("ProductionYear")
    if year is not None and str(year).strip() != "":
        try:
            return int(year)
        except (TypeError, ValueError):
            pass
    for key in ("PremiereDate", "StartDate", "EndDate", "DateCreated"):
        value = raw.get(key)
        if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
    return None


def _genres_from_jellyfin(raw: dict) -> list[str]:
    """Prefer Genres string list; fall back to GenreItems[].Name."""
    genres = raw.get("Genres")
    out: list[str] = []
    if isinstance(genres, list):
        for entry in genres:
            if isinstance(entry, str) and entry.strip():
                out.append(entry.strip())
            elif isinstance(entry, dict):
                name = entry.get("Name") or entry.get("name")
                if name:
                    out.append(str(name).strip())
    if out:
        return out
    items = raw.get("GenreItems") or []
    if isinstance(items, list):
        for entry in items:
            if isinstance(entry, dict):
                name = entry.get("Name") or entry.get("name")
                if name:
                    out.append(str(name).strip())
            elif isinstance(entry, str) and entry.strip():
                out.append(entry.strip())
    return out


def _rating_from_jellyfin(raw: dict) -> float:
    """CommunityRating (0–10). CriticRating is often 0–100 — normalize when needed."""
    community = raw.get("CommunityRating")
    if community is not None and community != "":
        try:
            return float(community)
        except (TypeError, ValueError):
            pass
    critic = raw.get("CriticRating")
    if critic is not None and critic != "":
        try:
            value = float(critic)
        except (TypeError, ValueError):
            return 0.0
        return value / 10.0 if value > 10 else value
    return 0.0


def _runtime_from_ticks(runtime_ticks: float) -> str:
    if not runtime_ticks:
        return ""
    minutes = int(runtime_ticks / 10_000_000 / 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if hours else f"{mins}m"


def _title_from_jellyfin(raw: dict) -> str:
    kind = raw.get("Type")
    name = str(raw.get("Name") or "").strip()
    series = str(raw.get("SeriesName") or "").strip()
    if kind == "Episode":
        # Wallpaper chrome wants the show, not "Chapter 1".
        if series:
            return series
        return name or "Untitled"
    return name or series or "Untitled"


class JellyfinProvider:
    name = "jellyfin"

    def __init__(self, url: str = "", api_key: str = "", user_id: str = "", client: HttpClient | None = None):
        self.url = (url or "").rstrip("/")
        self.api_key = api_key or ""
        self.user_id = user_id or ""
        self.client = client or HttpClient()

    def is_configured(self) -> bool:
        return bool(self.url and self.api_key)

    def auth_headers(self) -> dict[str, str]:
        auth = (
            'MediaBrowser Client="Wallpaparr", Device="wallpaparr", '
            f'DeviceId="wallpaparr", Version="{__version__}"'
        )
        if self.api_key:
            auth += f', Token="{self.api_key}"'
        return {"Authorization": auth, "X-Emby-Token": self.api_key}

    def _headers(self) -> dict[str, str]:
        return self.auth_headers()

    def test(self) -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "Jellyfin URL and API key are required"}
        try:
            info = self.client.get_json(f"{self.url}/System/Info/Public", headers=self._headers())
            return {"ok": True, "server": info.get("ServerName") or info.get("serverName") or "Jellyfin"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def list_items(self, limit: int = 40) -> list[MediaItem]:
        if not self.is_configured():
            return []
        user = self.user_id or self._first_user()
        params = {
            "IncludeItemTypes": _LIST_TYPES,
            "Recursive": "true",
            "Fields": (
                "Overview,Genres,GenreItems,OfficialRating,CommunityRating,CriticRating,"
                "ProviderIds,RunTimeTicks,UserData,ImageTags,BackdropImageTags,PremiereDate"
            ),
            "Limit": str(limit),
            "SortBy": "DateLastContentAdded,SortName",
            "SortOrder": "Descending",
            "ImageTypeLimit": "1",
            "EnableImageTypes": "Backdrop,Logo,Primary",
        }
        path = f"/Users/{user}/Items" if user else "/Items"
        payload = self.client.get_json(urljoin(self.url + "/", path.lstrip("/")), headers=self._headers(), params=params)
        items = payload.get("Items") if isinstance(payload, dict) else payload
        out: list[MediaItem] = []
        for raw in items or []:
            parsed = self._parse(raw, user)
            if parsed:
                out.append(parsed)
        return out

    def _first_user(self) -> str:
        try:
            users = self.client.get_json(f"{self.url}/Users", headers=self._headers())
            if isinstance(users, list) and users:
                return str(users[0].get("Id") or "")
        except Exception:
            return ""
        return ""

    def _parse(self, raw: dict, user: str) -> MediaItem | None:
        item_id = str(raw.get("Id") or "")
        if not item_id:
            return None
        kind = str(raw.get("Type") or "")
        # Some Jellyfin builds still return BoxSets under Movie,Series filters.
        if kind and kind not in _PARSE_TYPES:
            return None
        providers = raw.get("ProviderIds") or {}
        userdata = raw.get("UserData") or {}
        played = bool(userdata.get("Played"))
        position = float(userdata.get("PlaybackPositionTicks") or 0)
        # Series/Season UserData has no PlaybackPositionTicks (that only
        # applies to a single video) — Jellyfin instead reports an aggregate
        # PlayedPercentage across child episodes. Without this, a series with
        # a few watched episodes always read as "unwatched".
        played_pct = userdata.get("PlayedPercentage")
        runtime_ticks = float(raw.get("RunTimeTicks") or 0)
        if played:
            watch = "watched"
        elif position > 0 or (played_pct is not None and 0 < float(played_pct) < 100):
            watch = "partial"
        else:
            watch = "unwatched"
        is_tv = kind in ("Series", "Season", "Episode")
        # Episodes: prefer nested Series production year when present, else episode year / air date.
        nested = raw.get("Series") if isinstance(raw.get("Series"), dict) else None
        if kind == "Episode" and nested:
            year = _year_from_jellyfin(nested) or _year_from_jellyfin(raw)
        else:
            year = _year_from_jellyfin(raw)
        backdrop_url, logo_url, poster_url = self._artwork_urls(item_id, raw)
        return MediaItem(
            title=_title_from_jellyfin(raw),
            year=year,
            overview=str(raw.get("Overview") or ""),
            rating=_rating_from_jellyfin(raw),
            genres=_genres_from_jellyfin(raw),
            official_rating=str(raw.get("OfficialRating") or ""),
            runtime=_runtime_from_ticks(runtime_ticks),
            media_type="tv" if is_tv else "movie",
            watch_state=watch,
            library_state="in_library",
            availability="available",
            source="jellyfin",
            jellyfin_id=item_id,
            tmdb_id=str(providers.get("Tmdb") or "") or None,
            imdb_id=str(providers.get("Imdb") or "") or None,
            action_url=f"jellyfin://items/{item_id}",
            backdrop_url=backdrop_url,
            logo_url=logo_url,
            poster_url=poster_url,
        )

    def _image_url(self, item_id: str, kind: str, query: str = "") -> str | None:
        if not self.url:
            return None
        suffix = f"?{query}" if query else ""
        return f"{self.url}/Items/{item_id}/Images/{kind}{suffix}"

    def _artwork_urls(self, item_id: str, raw: dict) -> tuple[str | None, str | None, str | None]:
        tags = raw.get("ImageTags")
        backdrops = raw.get("BackdropImageTags")
        poster = self._image_url(item_id, "Primary", "maxHeight=600") if (not isinstance(tags, dict) or tags.get("Primary")) else None
        logo = self._image_url(item_id, "Logo") if (not isinstance(tags, dict) or tags.get("Logo")) else None
        if backdrops:
            backdrop = self._image_url(item_id, "Backdrop", "maxWidth=1920")
        elif isinstance(tags, dict) and tags.get("Primary"):
            backdrop = self._image_url(item_id, "Primary", "maxWidth=1920")
        elif isinstance(tags, dict) and tags.get("Thumb"):
            backdrop = self._image_url(item_id, "Thumb", "maxWidth=1920")
        elif tags is None and backdrops is None:
            backdrop = self._image_url(item_id, "Backdrop", "maxWidth=1920")
        else:
            backdrop = None
        return backdrop, logo, poster
