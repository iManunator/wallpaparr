from __future__ import annotations

import json
from typing import Protocol
from urllib.parse import urljoin, urlparse

import httpx

from app.models import MediaItem

# Artwork / JSON fetches used to buffer the entire body. A huge or non-http
# URL (file:, a 2 GB "image") can OOM the generate worker. Cap both.
MAX_BYTES = 20 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 5
_SENSITIVE_HEADERS = frozenset({"authorization", "x-emby-token", "x-api-key"})


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


def url_host(url: str) -> str:
    return urlparse(str(url or "")).netloc.lower()


def _strip_sensitive(headers: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in headers.items() if key.lower() not in _SENSITIVE_HEADERS}


def _read_capped(response: httpx.Response, max_bytes: int) -> bytes:
    declared = response.headers.get("content-length")
    if declared:
        try:
            if int(declared) > max_bytes:
                raise ValueError("response too large")
        except ValueError as exc:
            if "too large" in str(exc):
                raise
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes(65536):
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("response too large")
        chunks.append(chunk)
    return b"".join(chunks)


class HttpClient:
    def __init__(self, timeout: float = 15.0, transport: httpx.BaseTransport | None = None):
        self.timeout = timeout
        self.transport = transport

    def _client(self) -> httpx.Client:
        kwargs: dict = {"timeout": self.timeout, "follow_redirects": False}
        if self.transport is not None:
            kwargs["transport"] = self.transport
        return httpx.Client(**kwargs)

    def _get_capped(
        self,
        url: str,
        *,
        headers: dict | None = None,
        params: dict | None = None,
        max_bytes: int = MAX_BYTES,
    ) -> bytes:
        current = require_http_url(url)
        start_host = url_host(current)
        hdrs = dict(headers or {})
        query = params
        with self._client() as client:
            for _ in range(MAX_REDIRECTS + 1):
                if url_host(current) != start_host:
                    hdrs = _strip_sensitive(hdrs)
                with client.stream("GET", current, headers=hdrs or None, params=query) as response:
                    query = None
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            response.raise_for_status()
                            raise ValueError("redirect without Location")
                        current = require_http_url(urljoin(current, location))
                        continue
                    response.raise_for_status()
                    return _read_capped(response, max_bytes)
        raise ValueError("too many redirects")

    def get_json(self, url: str, headers: dict | None = None, params: dict | None = None) -> dict | list:
        payload = json.loads(self._get_capped(url, headers=headers, params=params, max_bytes=MAX_JSON_BYTES))
        return payload

    def get_bytes(self, url: str, headers: dict | None = None) -> bytes:
        return self._get_capped(url, headers=headers, max_bytes=MAX_BYTES)
