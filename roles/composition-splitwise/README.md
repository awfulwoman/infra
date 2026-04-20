# Splitwise

Deploys a self-hosted expense-splitting web application built on a custom Python/FastAPI stack. The role copies the application source from `files/app/` into the composition config directory, builds it as a Docker image, and initialises an empty `users.json` data store on first run. Groups and expenses are stored as JSON files under `data/`.

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_splitwise_port` | `8000` | Internal application port |
| `composition_splitwise_subdomain` | `splitwise.<host_name>` | Traefik subdomain (without domain suffix) |
| `composition_splitwise_domain` | `splitwise.<host_name>.<domain>` | Full public hostname |
| `composition_splitwise_mqtt_broker` | `mqtt.<domain>` | MQTT broker hostname for event publishing |
| `composition_splitwise_mqtt_port` | `1883` | MQTT broker port |
| `composition_splitwise_admin_username` | `admin` | Admin account username |
| `composition_splitwise_admin_password` | vault | Admin password — stored in Ansible Vault as `vault_splitwise_admin_password` |
| `composition_splitwise_default_currency` | `EUR` | Default currency for new groups |

## Integrations

- **Traefik**: Exposed via HTTPS at `composition_splitwise_domain` with Let's Encrypt TLS
- **MQTT**: Publishes events to the configured MQTT broker (e.g. for Home Assistant automations)
- **DNS**: Registers `composition_splitwise_subdomain` via `network-register-subdomain`
