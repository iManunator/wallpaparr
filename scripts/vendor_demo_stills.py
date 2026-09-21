#!/usr/bin/env python3
"""Re-vendor license-safe 1920×1080 demo stills from Wikimedia Commons.

Run from the repo root (optional). The JPEGs in backend/app/demo_stills/ are
already committed so CI / first boot do not need the network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend" / "app" / "demo_stills" / "catalog.json"


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    print("Demo stills are vendored next to catalog.json.")
    print("To refresh crops, re-run the Commons download used when this catalog was written.")
    print()
    for row in catalog:
        print(f"- {row['title']}: {row['commons_title']} ({row['license']})")
        print(f"  {row['commons_page']}")
    print()
    print("Attribution: backend/app/demo_stills/ATTRIBUTION.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
