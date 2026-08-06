#!/bin/bash
# Capture DNS + TLS state for every registered service name, from a LAN vantage
# (this machine) and a remote vantage (public01). Run before any DNS/TLS change
# and diff docs/snapshots/ against the result afterwards.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

OUT_DIR="docs/snapshots"
NAMES_FILE="scripts/snapshot-domains-names.json"
REMOTE_HOST="public01"

mkdir -p "$OUT_DIR"
trap 'rm -f "$NAMES_FILE"' EXIT

echo "==> Deriving service names from inventory"
ansible-playbook playbooks/utility/export-service-names.yaml >/dev/null

echo "==> Capturing LAN vantage"
python3 scripts/snapshot-domains.py "$NAMES_FILE" --vantage lan --output "$OUT_DIR/domains-lan.json"

echo "==> Capturing remote vantage ($REMOTE_HOST)"
REMOTE_TMP="$(ssh "$REMOTE_HOST" mktemp -d)"
scp -q "$NAMES_FILE" scripts/snapshot-domains.py "$REMOTE_HOST:$REMOTE_TMP/"
ssh "$REMOTE_HOST" "python3 $REMOTE_TMP/snapshot-domains.py $REMOTE_TMP/$(basename "$NAMES_FILE") --vantage remote --output $REMOTE_TMP/domains-remote.json"
scp -q "$REMOTE_HOST:$REMOTE_TMP/domains-remote.json" "$OUT_DIR/domains-remote.json"
ssh "$REMOTE_HOST" rm -rf "$REMOTE_TMP"

echo "==> Done. Snapshots written to $OUT_DIR/"
echo "    Diff against the committed baseline with: git diff -- $OUT_DIR"
