#!/bin/bash
# Flush DNS cache on MacOS
# Usage: sudo ./flush-dns.sh

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo" >&2
  exit 1
fi

dscacheutil -flushcache
killall -HUP mDNSResponder

echo "DNS cache flushed"
