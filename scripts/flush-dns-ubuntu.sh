#!/bin/bash
# Flush DNS cache on Ubuntu
# Usage: sudo ./flush-dns-ubuntu.sh

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo" >&2
  exit 1
fi

systemctl restart systemd-resolved

echo "DNS cache flushed"
