#!/bin/sh
# Email backup sync script using mbsync (isync)

set -e

echo "Starting email backup sync at $(date)"

# Install mbsync if not present
if ! command -v mbsync >/dev/null 2>&1; then
  echo "Installing isync (mbsync)..."
  apk add --no-cache isync ca-certificates
fi

# Create sync state directory
mkdir -p /data/.mbsync

# Run mbsync to backup all folders to local Maildir
mbsync -c /root/.mbsyncrc -V main

echo "Email backup sync completed at $(date)"
echo "Maildir stored in: /data/"
