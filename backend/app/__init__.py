"""Wallpaparr backend — cinematic Projectivy wallpapers."""

from pathlib import Path


def _read_version() -> str:
    """Product version lives in the repo-root ``VERSION`` file (see docs/RELEASE.md)."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[2] / "VERSION",  # repo root when running from source
        Path("/app/VERSION"),  # Docker image (COPY VERSION /app/VERSION)
        here.parents[1] / "VERSION",
    )
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text.splitlines()[0].strip()
    return "0.0.0"


__version__ = _read_version()
