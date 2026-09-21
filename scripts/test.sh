#!/usr/bin/env bash
# Unit/integration tests (no Docker, no Jellyfin).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> backend pytest"
VENV="$ROOT/backend/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "creating backend/.venv (PEP 668 — do not pip-install into the system Python)"
  if ! python3 -m venv "$VENV"; then
    echo "python3 -m venv failed. Install python3-venv, then: python3 -m venv backend/.venv" >&2
    exit 1
  fi
fi
"$VENV/bin/python" -m pip install -q -U pip
"$VENV/bin/python" -m pip install -q -r "$ROOT/backend/requirements-dev.txt"
(cd "$ROOT/backend" && "$VENV/bin/python" -m pytest -q)

echo "==> frontend vitest"
if [[ ! -d "$ROOT/web/node_modules" ]]; then
  (cd "$ROOT/web" && npm ci)
fi
(cd "$ROOT/web" && npm test)

echo "==> plugin :core:test"
(cd "$ROOT/plugin" && ./gradlew :core:test --no-daemon)
