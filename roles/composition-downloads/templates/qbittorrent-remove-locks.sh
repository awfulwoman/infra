#!/bin/bash
# qBittorrent lock files are meaningless in a container (single-instance is
# guaranteed by Docker) and cause a crash loop after unclean shutdown because
# the stale PID/socket from the previous container run persists in the volume.
rm -f \
    /config/qBittorrent/lockfile \
    /config/qBittorrent/ipc-socket \
    /config/qBittorrent/qBittorrent-data.conf.lock
