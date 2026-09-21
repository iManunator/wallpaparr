"""Shared image sniffing for generate + the artwork proxy."""

from __future__ import annotations


def looks_like_image(data: bytes | None) -> bool:
    if not data:
        return False
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return True
    head = data.lstrip()[:16].lower()
    if head.startswith(b"<") or head.startswith(b"<!doctype"):
        return False
    return False


def image_media_type(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"
