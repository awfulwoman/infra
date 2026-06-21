#!/bin/bash
# Reports OS and available healthcheck tools for a Docker image.
# Usage: check-image-healthcheck-tools.sh <image>

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: $0 <image>" >&2
  exit 1
fi

IMAGE="$1"

echo "Probing $IMAGE..."
echo ""

docker run --rm --pull missing --entrypoint="" "$IMAGE" sh -c '
  echo "=== OS ==="
  cat /etc/os-release 2>/dev/null | grep -E "^(ID|PRETTY_NAME)=" || echo "(no /etc/os-release)"
  echo ""
  echo "=== Shells ==="
  for bin in sh bash dash ash; do
    path=$(which $bin 2>/dev/null) && echo "  $bin -> $path" || true
  done
  echo ""
  echo "=== Healthcheck tools ==="
  for bin in wget curl nc netcat; do
    path=$(which $bin 2>/dev/null) && echo "  $bin -> $path" || true
  done
  echo ""
  echo "=== Recommended healthcheck ==="
  if which bash >/dev/null 2>&1; then
    echo "  bash is available — use: bash -c '"'"'echo > /dev/tcp/localhost/PORT'"'"'"
  elif which wget >/dev/null 2>&1; then
    echo "  wget is available — use: wget -q --spider http://localhost:PORT/ || exit 1"
  elif which curl >/dev/null 2>&1; then
    echo "  curl is available — use: curl -sf http://localhost:PORT/ > /dev/null"
  elif which nc >/dev/null 2>&1; then
    echo "  nc is available — use: nc -z localhost PORT"
  else
    echo "  WARNING: no suitable healthcheck tool found"
  fi
'
