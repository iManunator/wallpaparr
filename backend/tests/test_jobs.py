from __future__ import annotations


def test_record_event_persists(suite_dirs):
    from app.ops import load_ops, record_event

    record_event("generate", {"layout": "Netflix Hero", "count": 3, "ok": True})
    data = load_ops()
    assert data["generate"]["ok"] is True
    assert data["generate"]["layout"] == "Netflix Hero"
    assert data["generate"]["count"] == 3
    assert data["generate"]["at"] > 0


def test_run_job_writes_cron_event(suite_dirs):
    from app.jobs import _run_job
    from app.ops import load_ops

    _run_job(
        layout="Google TV Clean",
        source="demo",
        skip_existing=False,
        replace_existing=False,
        cleanup=False,
        motion=False,
        limit=1,
        ids=["demo-jf-1"],
        skip_ids=[],
    )
    ops = load_ops()
    assert ops["cron"]["ok"] is True
    assert ops["cron"]["layout"] == "Google TV Clean"
    assert ops["cron"]["count"] == 1
    assert ops["cron"]["skipped"] == 0


def test_run_now_uses_demo_defaults(suite_dirs):
    from app.jobs import run_now

    result = run_now(
        {
            "layout": "Netflix Hero",
            "source": "demo",
            "skip_existing": False,
            "replace_existing": False,
            "cleanup": False,
            "motion": False,
            "limit": 1,
            "ids": ["demo-jf-2"],
        }
    )
    assert result["count"] == 1
    assert "Harbor Season" in result["created"]
    assert result["message"]
