# Guinea Cameras

Deploys four [uStreamer](https://github.com/pikvm/ustreamer) instances to stream live video from four USB webcams pointed at the guinea pig enclosure. Each camera is mapped from a host `/dev/videoN` device into the container and exposed on its own port. The user is added to the `video` group to allow device access.

## Streams

| Container | Host port | Host device | Traefik subdomain |
|---|---|---|---|
| guineacam01 | 18001 | /dev/video0 | `guineacams.<domain>` |
| guineacam02 | 18002 | /dev/video2 | — |
| guineacam03 | 18003 | /dev/video4 | — |
| guineacam04 | 18004 | /dev/video6 | — |

## Integrations

- **Traefik**: Containers expose labels for Traefik discovery; routing rules are expected to be configured via host_vars or a provider file
- **DNS**: Registers `guineacams` subdomain via `network-register-subdomain`
- **Permissions**: Ansible adds `ansible_user` to the `video` and `docker` groups on the target host
