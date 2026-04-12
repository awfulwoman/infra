# VictoriaMetrics

Centralized time-series database for long-term storage and querying of ZFS metrics.

## Overview

This composition provides a VictoriaMetrics single-node deployment that scrapes
ZFS metrics from all `zfs-api` instances across the infrastructure. It stores
metrics long-term in a compressed format and provides both a web UI (vmui) and
API for querying.

**Key Features:**

- Prometheus-compatible time-series database
- Automatic scraping of all zfs-api endpoints
- 1-year default retention (configurable)
- Built-in web UI (vmui) for query and visualization
- PromQL query support
- Efficient compression (~10x better than vanilla Prometheus)
- Self-monitoring metrics

## Architecture

**Stack:**

- **VictoriaMetrics**: Single-node time-series database
- **Docker**: Containerized deployment
- **Traefik**: Reverse proxy with automatic HTTPS

**Data Flow:**

```text
zfs-api endpoints → VictoriaMetrics scraper → Storage → vmui/API → Users
```

VictoriaMetrics runs with integrated Prometheus-compatible scraper that polls
all configured zfs-api instances every 60 seconds.
