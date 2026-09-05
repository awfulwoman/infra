# composition-logtide-agent

This role ships this host's Docker container logs to [Logtide](https://logtide.dev). It runs [Fluent Bit](https://fluentbit.io/) as a single container that tails `/var/lib/docker/containers/*/*.log` and POSTs the logs to the Logtide ingest API over HTTPS.

Tailing happens at the log-driver level, not per container. Every container on the host that uses the default `json-file` driver is collected, including ones added later, with no per-composition wiring. This role does not cover hosts that override the Docker log driver.

Deploy it by adding `logtide-agent` to a host's `compositions:` list.

## Relationship to the other logtide roles

| Role | Runs on | Collects |
| --- | --- | --- |
| `composition-logtide` | storage only | The Logtide server, plus the syslog listener on 514 |
| `composition-logtide-agent` | every Linux Docker host | That host's container logs |
| `system-logtide-syslog` | every Linux host | That host's system logs, via rsyslog to 514 |
| `system-logtide-fluent-bit-macos` | malcolm | macOS system + Ollama logs |

This role is safe to deploy on storage: `composition-logtide` no longer tails containers itself, so there is no double ingestion.

## Notes

**`hostname` is what disambiguates containers.** Logtide's `service` field is the container name, and `traefik`, `watchtower` and `zfs-api` all run on more than one host. The agent adds `hostname` to every record. You can query it as `metadata->>'hostname'`.

**No `docker.sock` mount.** Container names come from each container's `config.v2.json`, read from the log directory, so the agent never needs the socket. The log mount is read-only.

**Position database.** `composition_logtide_agent_state_dir` (default `/var/lib/logtide-agent`) holds Fluent Bit's read position for each file. On restart, the agent resumes from this position instead of skipping data written while it was down. It lives outside the composition's ZFS dataset on purpose. Fluent Bit rewrites it on every flush, and the compositions dataset uses `policy: critical` with `snapshots_discover_children`. `state: absent` does not remove it, by design.

**Exclusions.** `composition_logtide_agent_exclude_pattern` defaults to `^logtide-(backend|worker|agent)`. Without this exclusion, each of those feeds its own output back in: the backend logs every ingest request, the worker logs a line per batch it processes (including batches of its own lines, so it never idles), and the agent tails its own stdout. The rest of the stack — postgres, redis, frontend, fluent-bit — is ingested normally. This is what you want when Logtide itself is the thing that misbehaves.

**No healthcheck.** This matches the other Fluent Bit container: the image's contents are not confirmed to include a usable probe (see `.claude/rules/docker-healthcheck.md`). Check it with `docker logs logtide-agent`, which is quiet at the default `warn` level.
