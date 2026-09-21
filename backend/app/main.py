"""FastAPI application: wallpaper API + editor SPA."""

from __future__ import annotations

import base64
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import router
from app.config import ensure_dirs
from app.generate import seed_demo_catalog
from app.jobs import shutdown_scheduler, start_scheduler
from app.layouts import seed_presets

# Plugin + healthcheck stay reachable without a password so the TV and Docker
# HEALTHCHECK keep working. Everything else (SPA, settings, generate, delete)
# is gated when WALLPAPARR_AUTH_USER and WALLPAPARR_AUTH_PASSWORD are both set.
_PLUGIN_GET_EXACT = frozenset(
    {
        "/api/health",
        "/api/wallpaper/status",
        "/api/layouts/list",
        "/api/layouts/with-images",
        "/api/genres/list",
        "/api/ages/list",
        "/api/year/list",
    }
)


def auth_credentials() -> tuple[str, str]:
    return (
        os.environ.get("WALLPAPARR_AUTH_USER", "").strip(),
        os.environ.get("WALLPAPARR_AUTH_PASSWORD", "").strip(),
    )


def auth_is_public(method: str, path: str) -> bool:
    if method.upper() != "GET":
        return False
    if path in _PLUGIN_GET_EXACT:
        return True
    return path.startswith("/api/wallpaper/image/")


def _unauthorized() -> Response:
    return Response(
        content="Unauthorized",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Wallpaparr"'},
        media_type="text/plain",
    )


def _basic_user_password(header: str) -> tuple[str, str] | None:
    scheme, _, payload = header.partition(" ")
    if scheme.lower() != "basic" or not payload.strip():
        return None
    try:
        raw = base64.b64decode(payload.strip(), validate=True).decode("utf-8")
    except Exception:
        return None
    user, sep, password = raw.partition(":")
    if not sep:
        return None
    return user, password


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    seed_presets()
    if os.environ.get("SUITE_SKIP_SCHEDULER") != "1":
        start_scheduler()
    from app.catalog import load_catalog

    if os.environ.get("SUITE_SKIP_SEED") != "1" and not load_catalog():
        seed_demo_catalog(layout="Netflix Hero", limit=6)
    yield
    if os.environ.get("SUITE_SKIP_SCHEDULER") != "1":
        shutdown_scheduler()


app = FastAPI(
    title="Wallpaparr",
    version=__version__,
    lifespan=lifespan,
)


def _creds_match(given: str, expected: str) -> bool:
    if len(given) != len(expected):
        return False
    return secrets.compare_digest(given, expected)


@app.middleware("http")
async def optional_basic_auth(request: Request, call_next):
    user, password = auth_credentials()
    if not user or not password:
        return await call_next(request)
    if auth_is_public(request.method, request.url.path):
        return await call_next(request)
    parsed = _basic_user_password(request.headers.get("authorization") or "")
    if parsed and _creds_match(parsed[0], user) and _creds_match(parsed[1], password):
        return await call_next(request)
    return _unauthorized()


app.include_router(router)

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
