# Gitea Act Runners

Deploys [Gitea Act Runner](https://gitea.com/gitea/act_runner) instances that execute Gitea Actions CI/CD jobs. Runners connect to the Gitea instance at `gitea.{{ domainname_infra }}` and run jobs inside Docker containers. You can deploy runners on hosts separate from the Gitea server to distribute the load.

One runner (`runner01`) is active now. A second (`runner02`) is defined but commented out.

## Key Variables

| Variable | Purpose |
|----------|---------|
| `gitea_runner_registration` | Registration token from the Gitea instance (`vault_gitea_runner_registration`) |
| `gitea_runner_port` | Cache server port (default: `8999`) |

## Runner Configuration (`templates/config.yaml`)

- **Capacity**: 2 concurrent jobs per runner
- **Labels**: `ubuntu-latest`, `ubuntu-22.04`, `ubuntu-latest-slim`, `ubuntu-22.04-slim` (all Docker-based using official Gitea runner images)
- **Cache server**: Enabled, bound to the host's Tailscale IP (`ansible_facts['tailscale0']['ipv4']['address']`) on port `8999`, with `/opt/gitea/cache` as the cache directory
- **Tool cache**: `/opt/gitea/hostedtoolcache` mounted as `/opt/hostedtoolcache` inside the container

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/runner01` | Runner state and registration data |
| `/opt/gitea/cache` | Actions cache storage |
| `/opt/gitea/hostedtoolcache` | Hosted tool cache (e.g., Node, Python) |
| `/var/run/docker.sock` | Docker socket for spawning job containers |

## Notes

- Runs privileged to support Docker-in-Docker if needed.
- Job containers run on `{{ default_docker_network }}`.
- The runner name is `{{ ansible_facts['hostname'] }}-runner01`, for easy identification in the Gitea UI.
