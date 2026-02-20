# Composition Roles

Composition roles are Ansible roles that deploy Docker Compose applications. Each role follows the naming convention `composition-<name>` and encapsulates everything needed to run a containerised service: the Docker Compose file (templated with Jinja2), environment variables, and any supporting configuration.

This approach treats applications as declarative infrastructure. Rather than manually creating compose files on servers, Ansible renders them from templates using host-specific variables, ensuring consistency and reproducibility across the environment.

## Available Compositions

### Home Automation

The home automation stack centres on Home Assistant, with supporting services for device communication and voice control.

| Role                            | Description                                                       |
| ------------------------------- | ----------------------------------------------------------------- |
| `composition-homeassistant`     | Home Assistant and ESPHome for home automation                    |
| `composition-zigbee2mqtt`       | Zigbee to MQTT bridge for smart home devices                      |
| `composition-matter`            | Matter Server for controlling Matter devices over Wi-Fi or Thread |
| `composition-mqtt`              | MQTT message broker                                               |
| `composition-piper`             | Neural text-to-speech engine for Home Assistant voice             |
| `composition-wyoming-satellite` | Voice assistant satellite for Home Assistant                      |
| `composition-musicassistant`    | Music library management and streaming for Home Assistant         |

### Media & Entertainment

A self-hosted media ecosystem covering photo management, video streaming, and automated content acquisition.

| Role                      | Description                                               |
| ------------------------- | --------------------------------------------------------- |
| `composition-jellyfin`    | Media server for movies, TV shows, and music              |
| `composition-immich`      | High performance self-hosted photo and video management   |
| `composition-immich-ml`   | Machine learning sidecar for Immich photo recognition     |
| `composition-downloads`   | The \*arr stack for media automation                      |
| `composition-tubesync`    | Automated YouTube channel archival to local media library |
| `composition-get-iplayer` | BBC iPlayer programme downloader                          |
| `composition-iplayarr`    | Arr-style automation for BBC iPlayer content              |
| `composition-podcasts`    | Podcast downloader and manager                            |
| `composition-audio`       | Audio streaming and playback services                     |

### Productivity & Information

Tools for managing code, staying informed, and organising personal data.

| Role                         | Description                                     |
| ---------------------------- | ----------------------------------------------- |
| `composition-gitea`          | Git repository storage and CI/CD pipelines      |
| `composition-gitea-runners`  | CI/CD runners for Gitea Actions                 |
| `composition-freshrss`       | Self-hosted RSS feed aggregator                 |
| `composition-syncthing`      | Continuous file synchronisation between devices |
| `composition-karakeep`       | Bookmark and read-later content manager         |
| `composition-finances`       | Personal finance tracking and budgeting         |
| `composition-libretranslate` | Self-hosted translation service                 |

### Networking & Infrastructure

Services that support the broader infrastructure: ingress routing, DNS, and visibility into network activity.

| Role                               | Description                                           |
| ---------------------------------- | ----------------------------------------------------- |
| `composition-reverseproxy`         | Traefik-based ingress with automatic TLS certificates |
| `composition-pihole`               | Network-wide DNS ad blocker and local DNS management  |
| `composition-watchyourlan`         | Network device discovery and monitoring               |
| `composition-ladder`               | Privacy-preserving web proxy for bypassing paywalls   |
| `composition-container-management` | Tools for managing Docker containers                  |
| `composition-homepage`             | Application dashboard and service monitoring          |

### Social & Communication

Federated social networking and location sharing.

| Role                     | Description                    |
| ------------------------ | ------------------------------ |
| `composition-gotosocial` | Fediverse server (ActivityPub) |
| `composition-owntracks`  | Location tracking and sharing  |

### Cameras & Surveillance

Camera feeds and motion detection for monitoring.

| Role                     | Description                            |
| ------------------------ | -------------------------------------- |
| `composition-motioneye`  | Webcam management and motion detection |
| `composition-guineacams` | Guinea pig cameras (pet monitoring)    |
| `composition-testcam`    | Test camera configuration              |

### Static Sites

| Role                     | Description             |
| ------------------------ | ----------------------- |
| `composition-awfulwoman` | Static HTML site server |
