# Nominatim

[Nominatim](https://nominatim.org/) is a search engine for OpenStreetMap data, providing geocoding (place name → coordinates) and reverse geocoding (coordinates → place name).

## Configuration

Before first run, set `nominatim_pbf_url` in `host_vars` to a PBF extract for your region from [Geofabrik](https://download.geofabrik.de/). The container downloads and imports the data on first start — small regions take minutes, large ones (country/continent) can take hours.

Set `nominatim_update_mode: continuous` to keep the database in sync with OSM changes via the replication URL.

The PostgreSQL memory defaults (`512MB` shared buffers, `1GB` effective cache) are conservative for home servers. Increase them for faster imports and queries if RAM permits.

## Ports

| Port | Service |
|------|---------|
| `8080` | Nominatim API |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/postgres` | PostgreSQL 16 data (OSM import) |
| `{{ composition_config }}/flatnode` | Flatnode file (speeds up large-region imports) |

## Integrations

- **Traefik**: Exposed at `nominatim.{{ domainname_infra }}` with Let's Encrypt TLS.

## Notes

All services (PostgreSQL 16 + Nominatim API) run in a single container. The image tag is pinned to `5.3`; check the [upstream repo](https://github.com/mediagis/nominatim-docker) for newer releases.
