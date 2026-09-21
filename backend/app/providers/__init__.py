from __future__ import annotations

from typing import Protocol
from urllib.parse import urlparse

import httpx

from app.models import MediaItem

# Artwork / JSON fetches used to buffer the entire body. A huge or non-http
# URL (file:, a 2 GB "image") can OOM the generate worker. Cap both.
MAX_BYTES = 20 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024


class Provider(Protocol):
    name: str

    def is_configured(self) -> bool: ...
    def list_items(self, limit: int = 40) -> list[MediaItem]: ...
    def test(self) -> dict: ...


def require_http_url(url: str) -> str:
    """Reject non-http(s) schemes (file:, gopher:, etc.)."""
    text = str(url or "").strip()
    parsed = urlparse(text)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"unsupported URL: {text[:80]}")
    return text


class HttpClient:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def get_json(self, url: str, headers: dict | None = None, params: dict | None = None) -> dict | list:
        require_http_url(url)
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            if len(response.content) > MAX_JSON_BYTES:
                raise ValueError("response too large")
            return response.json()

    def get_bytes(self, url: str, headers: dict | None = None) -> bytes:
        require_http_url(url)
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > MAX_BYTES:
                            raise ValueError("response too large")
                    except (TypeError, ValueError) as exc:
                        if "too large" in str(exc):
                            raise
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes(65536):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("response too large")
                    chunks.append(chunk)
                return b"".join(chunks)
