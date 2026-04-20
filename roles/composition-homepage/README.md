# Homepage

[Homepage](https://gethomepage.dev) is a self-hosted dashboard providing a customisable start page with service widgets, bookmarks, and Docker container status. It is the primary entry point to the home infrastructure, accessible at `home.<domain>`.

The role templates all Homepage configuration files (`services.yaml`, `bookmarks.yaml`, `settings.yaml`, `widgets.yaml`, `docker.yaml`, `kubernetes.yaml`, `custom.css`, `custom.js`) directly into the container's config directory. Background images are downloaded from Unsplash at deploy time.

Homepage has access to the Docker socket to display live container status widgets for other services.

## Ports

Internal port `3000`, bound to `127.0.0.1:3648` on the host. Exposed via Traefik at `home.<domain>`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/homepage` | All YAML/CSS/JS config files |
| `{{ composition_config }}/images` | Background images (`mountains.jpg`, `meteor.jpg`) |
| `/var/run/docker.sock` | Docker socket for container status widgets |

## DNS

Registers subdomain: `home`
