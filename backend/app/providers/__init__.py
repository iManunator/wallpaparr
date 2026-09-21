from __future__ import annotations

from typing import Protocol

import httpx

from app.models import MediaItem


class Provider(Protocol):
    name: str

    def is_configured(self) -> bool: ...
    def list_items(self, limit: int = 40) -> list[MediaItem]: ...
    def test(self) -> dict: ...


class HttpClient:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def get_json(self, url: str, headers: dict | None = None, params: dict | None = None) -> dict | list:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    def get_bytes(self, url: str, headers: dict | None = None) -> bytes:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.content
