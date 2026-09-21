from __future__ import annotations

import httpx
import pytest

from app.providers import HttpClient, MAX_JSON_BYTES, require_http_url


def test_require_http_url_accepts_http_https():
    assert require_http_url("https://image.tmdb.org/t/p/w500/x.jpg").startswith("https://")
    assert require_http_url("http://jf:8096/Items/1/Images/Backdrop").startswith("http://")


def test_require_http_url_rejects_non_http():
    with pytest.raises(ValueError):
        require_http_url("file:///etc/passwd")
    with pytest.raises(ValueError):
        require_http_url("gopher://example")
    with pytest.raises(ValueError):
        require_http_url("/etc/passwd")
    with pytest.raises(ValueError):
        require_http_url("")


def _client(handler) -> HttpClient:
    return HttpClient(transport=httpx.MockTransport(handler))


def test_cross_host_redirect_strips_auth_headers():
    seen: list[tuple[str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), dict(request.headers)))
        if request.url.host == "jf":
            return httpx.Response(302, headers={"Location": "http://cdn.example/art.jpg"})
        return httpx.Response(200, content=b'{"ok": true}')

    payload = _client(handler).get_json(
        "http://jf:8096/Items/1",
        headers={"Authorization": "MediaBrowser Token=secret", "X-Emby-Token": "secret", "X-Api-Key": "seerr"},
    )
    assert payload == {"ok": True}
    assert seen[0][0].startswith("http://jf:8096/")
    assert seen[0][1]["authorization"] == "MediaBrowser Token=secret"
    assert seen[0][1]["x-emby-token"] == "secret"
    assert seen[1][0] == "http://cdn.example/art.jpg"
    assert "authorization" not in seen[1][1]
    assert "x-emby-token" not in seen[1][1]
    assert "x-api-key" not in seen[1][1]


def test_same_host_redirect_keeps_auth_headers():
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.headers))
        if request.url.path == "/old":
            return httpx.Response(302, headers={"Location": "/Items/1/Images/Backdrop"})
        return httpx.Response(200, content=b"\xff\xd8\xff" + b"\x00" * 8)

    data = _client(handler).get_bytes(
        "http://jf:8096/old",
        headers={"Authorization": "MediaBrowser Token=secret", "X-Emby-Token": "secret"},
    )
    assert data.startswith(b"\xff\xd8\xff")
    assert seen[1]["authorization"] == "MediaBrowser Token=secret"
    assert seen[1]["x-emby-token"] == "secret"


def test_redirect_to_file_url_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "file:///etc/passwd"})

    with pytest.raises(ValueError, match="unsupported URL"):
        _client(handler).get_bytes("http://jf:8096/Items/1/Images/Backdrop")


def test_get_json_caps_body_size():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{" + b"x" * (MAX_JSON_BYTES + 1) + b"}")

    with pytest.raises(ValueError, match="too large"):
        _client(handler).get_json("http://jf:8096/Items")
