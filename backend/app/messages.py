"""User-facing connection and generate copy (toasts / banners)."""

from __future__ import annotations

from typing import Any

PROVIDER_LABELS = {
    "jellyfin": "Jellyfin",
    "jellyseerr": "Jellyseerr / Seerr",
    "seerr": "Jellyseerr / Seerr",
    "tmdb": "TMDB",
    "demo": "the demo catalog",
}


def provider_test_message(provider: str, result: dict[str, Any]) -> str:
    key = (provider or "").lower()
    label = PROVIDER_LABELS.get(key, provider or "provider")
    if result.get("ok"):
        server = str(result.get("server") or "").strip()
        if key == "demo":
            return "Demo catalog ready — license-safe cinematic stills, no Jellyfin required"
        if key == "tmdb":
            return "Connected to TMDB"
        if key in ("jellyseerr", "seerr"):
            extra = f" (version {server})" if server and server.lower() not in {"seerr", "jellyseerr"} else ""
            return f"Connected to Jellyseerr / Seerr{extra}"
        extra = f" ({server})" if server else ""
        return f"Connected to {label}{extra}"
    error = str(result.get("error") or "unknown error").strip()
    if "required" in error.lower():
        return error if error[0].isupper() else error[:1].upper() + error[1:]
    if "api key" in error.lower() or "rejected" in error.lower():
        return error
    return f"Could not reach {label}: {error}"


def enrich_provider_result(provider: str, result: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["provider"] = (provider or "").lower()
    out["message"] = provider_test_message(provider, result)
    return out


def generate_message(layout: str, result: dict[str, Any]) -> str:
    created_titles = list(result.get("created") or [])
    created = len(created_titles)
    skipped = len(result.get("skipped") or [])
    replaced = len(result.get("replaced") or [])
    refreshed = len(result.get("refreshed") or [])
    cleaned = len(result.get("cleaned") or [])
    failed = len(result.get("failed") or [])
    if created:
        head = f"Created {created} still{'s' if created != 1 else ''} for {layout}"
        if created <= 3:
            head += f" ({', '.join(created_titles)})"
    else:
        head = f"No new stills for {layout}"
    bits: list[str] = []
    if replaced:
        bits.append(f"replaced {replaced}")
    if refreshed:
        bits.append(f"refreshed {refreshed} status change{'s' if refreshed != 1 else ''}")
    if skipped:
        bits.append(f"skipped {skipped} already generated")
    if cleaned:
        bits.append(f"cleaned {cleaned}")
    if failed:
        bits.append(f"{failed} failed")
    msg = head if not bits else f"{head} — {', '.join(bits)}"
    warnings = result.get("warnings") or []
    if warnings:
        msg += f". {warnings[0]}"
    if not msg.endswith("."):
        msg += "."
    return msg


def motion_bake_message(layout: str, result: dict[str, Any]) -> str:
    generated = list(result.get("generated") or [])
    failed = list(result.get("failed") or [])
    n = len(generated)
    style = str(result.get("style") or "parallax")
    preset = str(result.get("preset") or "cinematic")
    duration = result.get("duration")
    loop = f", {duration:g}s loop" if duration else ""
    if n == 1:
        head = f"Baked {style} VIDEO for {generated[0]} on {layout} ({preset}{loop})"
    elif n:
        head = f"Baked {style} VIDEO for {n} titles on {layout} ({preset}{loop})"
    else:
        head = f"No VIDEO clips baked for {layout}"
        if failed:
            head += f" — {len(failed)} failed"
        else:
            head += " (need stills and ffmpeg)"
    if failed and n:
        head += f" — {len(failed)} failed"
    if not head.endswith("."):
        head += "."
    return head
