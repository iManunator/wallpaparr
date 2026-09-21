"""In-process cron scheduler for wallpaper generation."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import load_settings
from app.generate import run_generate
from app.models import GenerateRequest

_scheduler: BackgroundScheduler | None = None


def cron_expr(job: dict | None) -> str:
    spec = job or {}
    return str(spec.get("cron") or spec.get("schedule") or "0 4 * * *")


def cron_parse_error(expr: str) -> str | None:
    """Return a short reason if ``expr`` is not a 5-field crontab, else None."""
    try:
        CronTrigger.from_crontab(expr)
    except Exception as exc:
        return str(exc) or "invalid cron expression"
    return None


def invalid_cron_jobs(jobs: list | None, *, enabled_only: bool = True) -> list[dict]:
    """Jobs whose crontab would be skipped by :func:`reload_jobs`."""
    errors: list[dict] = []
    for index, job in enumerate(jobs or []):
        spec = job or {}
        if enabled_only and not spec.get("enabled", True):
            continue
        expr = cron_expr(spec)
        reason = cron_parse_error(expr)
        if reason:
            errors.append(
                {
                    "index": index,
                    "name": spec.get("name") or f"Schedule {index + 1}",
                    "cron": expr,
                    "error": reason,
                }
            )
    return errors


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        reload_jobs()
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    reload_jobs()
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def reload_jobs() -> None:
    if _scheduler is None:
        return
    _scheduler.remove_all_jobs()
    settings = load_settings()
    skipped = invalid_cron_jobs(settings.cron_jobs, enabled_only=True)
    if skipped:
        from app.ops import record_event

        record_event("cron_errors", {"jobs": skipped, "count": len(skipped)})
    else:
        from app.ops import load_ops, record_event

        if load_ops().get("cron_errors"):
            record_event("cron_errors", {"jobs": [], "count": 0})
    for index, job in enumerate(settings.cron_jobs or []):
        if not job.get("enabled", True):
            continue
        expr = cron_expr(job)
        try:
            trigger = CronTrigger.from_crontab(expr)
        except Exception:
            continue
        _scheduler.add_job(
            _run_job,
            trigger=trigger,
            id=f"cron-{index}",
            replace_existing=True,
            kwargs=_job_kwargs(job),
        )


def _job_kwargs(job: dict | None) -> dict:
    spec = dict(job or {})
    ids = spec.get("ids") or []
    skip_ids = spec.get("skip_ids") or []
    if isinstance(ids, str):
        ids = [part.strip() for part in ids.split(",") if part.strip()]
    if isinstance(skip_ids, str):
        skip_ids = [part.strip() for part in skip_ids.split(",") if part.strip()]
    return {
        "layout": spec.get("layout") or "Netflix Hero",
        "source": spec.get("source") or "demo",
        "skip_existing": bool(spec.get("skip_existing", True)),
        "replace_existing": bool(spec.get("replace_existing", False)),
        "refresh_status": bool(spec.get("refresh_status", False)),
        "cleanup": bool(spec.get("cleanup", False)),
        "motion": bool(spec.get("motion", False)),
        "limit": int(spec.get("limit") or 20),
        "ids": list(ids),
        "skip_ids": list(skip_ids),
        "seerr_category": str(spec.get("seerr_category") or "trending"),
    }


def run_now(job: dict | None = None, job_id: str | None = None) -> dict:
    """Run a cron-shaped generate immediately (Settings → Run now)."""
    settings = load_settings()
    spec = dict(job or {})
    if not spec and settings.cron_jobs:
        spec = dict(settings.cron_jobs[0] or {})
    return _run_job(job_id=job_id, **_job_kwargs(spec))


def _run_job(job_id: str | None = None, **kwargs) -> dict:
    from app.ops import record_event

    request = GenerateRequest(**{k: v for k, v in kwargs.items() if k in GenerateRequest.model_fields})
    result = run_generate(request, job_id=job_id)
    record_event(
        "cron",
        {
            "layout": request.layout,
            "count": result.get("count"),
            "ok": True,
            "skipped": len(result.get("skipped") or []),
            "replaced": len(result.get("replaced") or []),
            "refreshed": len(result.get("refreshed") or []),
            "cleaned": len(result.get("cleaned") or []),
        },
    )
    return result
