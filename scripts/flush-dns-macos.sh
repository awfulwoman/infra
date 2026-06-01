#!/bin/bash
# Flush DNS cache on MacOS

sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Tailscale caches NXDOMAIN responses independently of the system DNS cache.
# Cycling the connection is the only reliable way to flush it.
# tailscale communicates via IPC socket — no sudo needed.
if command -v tailscale &>/dev/null; then
  tailscale down
  tailscale up
fi

echo "DNS cache flushed"
