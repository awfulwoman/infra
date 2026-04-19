# composition-splitwise

Deploys a self-hosted expense-splitting application as a Docker Compose service. Copies a custom Python application (FastAPI), initialises an empty `users.json` data store, and registers a per-host Traefik subdomain. Integrates with MQTT for event publishing and uses Ansible Vault for admin credentials.
