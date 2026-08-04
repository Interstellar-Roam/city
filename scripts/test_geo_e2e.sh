#!/bin/sh
set -eu

if command -v docker >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v podman >/dev/null 2>&1; then
  COMPOSE="podman compose"
else
  echo "Docker or Podman is required" >&2
  exit 1
fi

if [ "$(uname -m)" = "arm64" ] || [ "$(uname -m)" = "aarch64" ]; then
  POSTGIS_IMAGE="${POSTGIS_IMAGE:-imresamu/postgis:16-3.5-bundle0-bookworm}"
  POSTGIS_PLATFORM="${POSTGIS_PLATFORM:-linux/arm64}"
  export POSTGIS_IMAGE POSTGIS_PLATFORM
fi

$COMPOSE up -d --build --force-recreate mongodb postgres api
E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:8000}" uv run pytest tests/test_geo_e2e.py -v
