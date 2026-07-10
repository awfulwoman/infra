# Mastodon to KaraKeep

Syncs bookmarks from your Mastodon/GoToSocial account into [KaraKeep](https://karakeep.app/). Runs as a long-lived Docker container that polls the Mastodon bookmarks API on a configurable interval and imports any new bookmarks into KaraKeep, tagged with `mastodon`.

## Key Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `mastodon2karakeep_mastodon_base_url` | `https://{{ gotosocial_domain }}` | Base URL of your Mastodon/GoToSocial instance |
| `mastodon2karakeep_mastodon_token` | `{{ vault_mastodon2karakeep_token }}` | Mastodon access token with `read:bookmarks` scope |
| `mastodon2karakeep_kk_url` | `https://karakeep.{{ domainname_infra }}` | KaraKeep instance URL |
| `mastodon2karakeep_kk_token` | `{{ vault_karakeep_api }}` | KaraKeep API token |
| `mastodon2karakeep_poll_interval` | `3600` | Seconds between sync runs |
| `mastodon2karakeep_default_tag` | `mastodon` | Tag applied to all imported bookmarks |

## Setup

1. Create a Mastodon application at `https://gts.awfulwoman.com/settings/applications` with the `read:bookmarks` scope and copy the access token.

2. Encrypt the token and store it in `inventory/group_vars/infra/vault_mastodon2karakeep.yaml`:

   ```bash
   ansible-vault encrypt_string "$(cat)" --name 'vault_mastodon2karakeep_token'
   ```

3. Run the playbook:

   ```bash
   ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags composition-mastodon2karakeep
   ```

## Behaviour

- Tracks already-imported bookmark IDs in `/data/seen_ids.json` so each bookmark is only imported once.
- Follows Mastodon pagination to fetch all bookmarks on each run.
- For reblogs, imports the URL of the original post.
- No web UI; runs as a background daemon with no exposed ports.
- The Docker image is built locally from a Python 3.13 slim base.

## Integrations

- **KaraKeep** (`composition-karakeep`): Requires a running KaraKeep instance and a valid API token (`vault_karakeep_api`).
- **GoToSocial** (`composition-gotosocial`): Uses the GoToSocial domain as the Mastodon base URL by default.
