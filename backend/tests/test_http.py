from __future__ import annotations

import pytest

from app.providers import require_http_url


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
