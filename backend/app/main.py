"""FastAPI application: wallpaper API + editor SPA."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import router
from app.config import ensure_dirs
from app.generate import seed_demo_catalog
from app.jobs import shutdown_scheduler, start_scheduler
from app.layouts import seed_presets


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
app.include_router(router)

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
