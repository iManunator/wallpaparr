"""In-memory generate / motion / cron job progress for the web UI.

FastAPI is a single process here, so a thread + a dict is enough for the
editor to poll ``GET /api/jobs/{id}`` while a batch runs. One job at a time.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

_LOCK = threading.Lock()
_JOBS: dict[str, "JobState"] = {}
_LATEST: str | None = None


@dataclass
class JobState:
    id: str
    kind: str
    status: str = "queued"
    total: int = 0
    done: int = 0
    current: str | None = None
    message: str = ""
    created: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    error: str | None = None
    result: dict[str, Any] | None = None
    started_at: float = 0.0
    updated_at: float = 0.0
    cancel_requested: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "current": self.current,
            "message": self.message,
            "created": list(self.created),
            "failed": list(self.failed),
            "skipped": list(self.skipped),
            "error": self.error,
            "result": self.result,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "cancel_requested": self.cancel_requested,
            "percent": 100
            if self.status in {"done", "cancelled"}
            else (0 if self.total <= 0 else min(99, int(round(100 * self.done / max(self.total, 1))))),
        }


def running_job() -> JobState | None:
    with _LOCK:
        for job in _JOBS.values():
            if job.status in {"queued", "running"}:
                return job
    return None


def get_job(job_id: str) -> JobState | None:
    with _LOCK:
        return _JOBS.get(job_id)


def latest_job() -> JobState | None:
    with _LOCK:
        if _LATEST and _LATEST in _JOBS:
            return _JOBS[_LATEST]
        if not _JOBS:
            return None
        return max(_JOBS.values(), key=lambda job: job.updated_at or job.started_at)


def patch_job(job_id: str, **fields: Any) -> JobState | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return None
        for key, value in fields.items():
            if hasattr(job, key):
                setattr(job, key, value)
        job.updated_at = time.time()
        return job


def request_cancel(job_id: str) -> JobState | None:
    """Ask a running job to stop after the current title finishes."""
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job or job.status not in {"queued", "running"}:
            return None
        job.cancel_requested = True
        job.message = "Cancelling…"
        job.updated_at = time.time()
        return job


def is_cancelled(job_id: str | None) -> bool:
    if not job_id:
        return False
    with _LOCK:
        job = _JOBS.get(job_id)
        return bool(job and job.cancel_requested)


def report(job_id: str | None, **fields: Any) -> None:
    if not job_id:
        return
    patch_job(job_id, **fields)


def spawn(kind: str, worker: Callable[[str], dict[str, Any]], *, message: str = "Starting…") -> JobState:
    if running_job() is not None:
        raise RuntimeError("A job is already running")
    job = JobState(
        id=uuid.uuid4().hex[:12],
        kind=kind,
        status="queued",
        message=message,
        started_at=time.time(),
        updated_at=time.time(),
    )
    global _LATEST
    with _LOCK:
        _JOBS[job.id] = job
        _LATEST = job.id
        # Cap history so a long-lived process does not grow forever.
        if len(_JOBS) > 20:
            oldest = sorted(_JOBS.values(), key=lambda row: row.started_at)[: len(_JOBS) - 20]
            for stale in oldest:
                if stale.status in {"done", "error", "cancelled"}:
                    _JOBS.pop(stale.id, None)

    def _run() -> None:
        patch_job(job.id, status="running", message=message)
        try:
            result = worker(job.id) or {}
            cancelled = bool(result.get("cancelled")) or is_cancelled(job.id)
            try:
                result_done = int(result["done"] if result.get("done") is not None else result.get("count") or job.done or 0)
            except (TypeError, ValueError):
                result_done = job.done
            try:
                result_total = int(result.get("total") or job.total or result_done or 0)
            except (TypeError, ValueError):
                result_total = max(job.total, result_done)
            patch_job(
                job.id,
                status="cancelled" if cancelled else "done",
                result=result,
                message=str(
                    result.get("message")
                    or ("Cancelled" if cancelled else "Done")
                ),
                created=list(result.get("created") or result.get("generated") or []),
                failed=list(result.get("failed") or []),
                skipped=list(result.get("skipped") or []),
                done=result_done,
                total=max(result_total, job.total, result_done),
                current=None,
            )
        except Exception as exc:
            patch_job(job.id, status="error", error=str(exc), message=str(exc), current=None)

    threading.Thread(target=_run, daemon=True, name=f"wallpaparr-{kind}").start()
    return job


def idle_snapshot() -> dict[str, Any]:
    return {
        "id": None,
        "kind": None,
        "status": "idle",
        "total": 0,
        "done": 0,
        "current": None,
        "message": "",
        "created": [],
        "failed": [],
        "skipped": [],
        "error": None,
        "result": None,
        "percent": 0,
    }


def reset_for_tests() -> None:
    global _LATEST
    with _LOCK:
        _JOBS.clear()
        _LATEST = None
