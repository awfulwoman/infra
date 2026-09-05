#!/bin/bash
# One-time, manually-run migration from the old single-account emailbackup layout
# (folders directly under emailbackup_storage_path) to the multi-account layout
# this role now expects (emailbackup_storage_path/<account>/...).
#
# Run this ON THE STORAGE HOST, as the account that owns the Maildir, BEFORE
# applying the updated system-emailbackup role for the first time on an
# already-populated host:
#
#   scp migrate-to-multi-account.sh storage:/tmp/
#   ssh storage
#   /tmp/migrate-to-multi-account.sh --dry-run   personal /slowpool/charlie/email
#   /tmp/migrate-to-multi-account.sh             personal /slowpool/charlie/email
#
# Safe to re-run: every step is guarded, and it refuses to move anything once
# emailbackup_storage_path/<account>/ already exists (the sign a previous run
# already did the work).
#
# What it does, in order:
#   1. Stops the old emailbackup.timer/.service (idempotent if already stopped/gone).
#   2. Records a baseline: total message-file count and `du -sh` of the storage path.
#   3. Verifies the three known-stale folders (Amazon, INBOX/Amazon, Later) contain
#      no messages before removing them — see the design doc for how this was
#      confirmed empty on 2026-09-04. Refuses to touch a folder that isn't empty.
#   4. Moves every remaining top-level folder into <account>/.
#   5. Moves the corresponding .mbsync state files into .mbsync/<account>/ — this
#      is what makes step 4 free: mbsync's SyncState files are named by mailbox
#      ("INBOX", "Archive!2019", ...) with no channel prefix, so relocating them
#      alongside the Maildir preserves sync state exactly. A large re-download on
#      the next mbsync run means this step went wrong — see verify_baseline below.
#
# It does NOT restart the timer, template the new units, or apply Remove Near —
# that is the Ansible role's job, run after this script.

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  shift
fi

ACCOUNT="${1:-}"
STORAGE_PATH="${2:-}"

if [[ -z "$ACCOUNT" || -z "$STORAGE_PATH" ]]; then
  echo "Usage: $0 [--dry-run] <account-name> <emailbackup_storage_path>" >&2
  exit 1
fi

if [[ ! -d "$STORAGE_PATH" ]]; then
  echo "error: $STORAGE_PATH does not exist" >&2
  exit 1
fi

run() {
  if $DRY_RUN; then
    echo "+ (dry-run) $*"
  else
    echo "+ $*"
    "$@"
  fi
}

if [[ -d "$STORAGE_PATH/$ACCOUNT" ]]; then
  echo "error: $STORAGE_PATH/$ACCOUNT already exists — migration already ran?" >&2
  exit 1
fi

echo "== Stopping old units (best-effort) =="
run sudo systemctl stop emailbackup.timer 2>/dev/null || true
run sudo systemctl stop emailbackup.service 2>/dev/null || true

echo "== Baseline =="
BASELINE_COUNT=$(find "$STORAGE_PATH" -mindepth 1 -type f -not -path "$STORAGE_PATH/.mbsync/*" | wc -l | tr -d ' ')
BASELINE_SIZE=$(du -sh "$STORAGE_PATH" | cut -f1)
echo "message files: $BASELINE_COUNT, size: $BASELINE_SIZE"

echo "== Verifying known-stale folders are empty before removing them =="
for stale in "Amazon" "INBOX/Amazon" "Later"; do
  path="$STORAGE_PATH/$stale"
  if [[ -d "$path" ]]; then
    count=$(find "$path" -type f -not -name ".uidvalidity" | wc -l | tr -d ' ')
    if [[ "$count" -ne 0 ]]; then
      echo "error: $path is not empty ($count files) — refusing to remove it." >&2
      echo "This folder was expected to be empty; re-check before proceeding." >&2
      exit 1
    fi
    echo "confirmed empty: $stale"
  fi
done

echo "== Removing confirmed-empty stale folders and their state files =="
run rm -rf "$STORAGE_PATH/Amazon"
run rm -rf "$STORAGE_PATH/INBOX/Amazon"
run rm -rf "$STORAGE_PATH/Later"
run rm -f "$STORAGE_PATH/.mbsync/Amazon"
run rm -f "$STORAGE_PATH/.mbsync/INBOX!Amazon"
run rm -f "$STORAGE_PATH/.mbsync/Later"

echo "== Moving mail folders into $ACCOUNT/ =="
run mkdir -p "$STORAGE_PATH/$ACCOUNT"
for entry in "$STORAGE_PATH"/*; do
  name=$(basename "$entry")
  [[ "$name" == "$ACCOUNT" ]] && continue
  [[ "$name" == ".mbsync" ]] && continue
  run mv "$entry" "$STORAGE_PATH/$ACCOUNT/$name"
done

echo "== Moving mbsync state files into .mbsync/$ACCOUNT/ =="
run mkdir -p "$STORAGE_PATH/.mbsync/$ACCOUNT"
for entry in "$STORAGE_PATH/.mbsync"/*; do
  [[ -d "$entry" ]] && continue  # skip account subdirectories, including one we just made
  run mv "$entry" "$STORAGE_PATH/.mbsync/$ACCOUNT/"
done

if $DRY_RUN; then
  echo "== Dry run complete — nothing was changed =="
  exit 0
fi

echo "== Migration complete =="
echo "Baseline was: $BASELINE_COUNT files, $BASELINE_SIZE"
echo "Now apply the system-emailbackup role, then verify the first run of"
echo "emailbackup@${ACCOUNT}.service pulls ~0 new messages and file count/du still"
echo "match the baseline above. A large download means the state files ended up"
echo "in the wrong place — stop and investigate rather than letting it re-fetch."
