# translation-server

Runs [translation-server](https://github.com/awfulwoman/translation-server):
private document translation (mostly German → English) with translategemma on
Malcolm's Ollama. Two containers from one image:

| Container | Command | Job |
| --- | --- | --- |
| `translation-server` | `serve` | DeepL v2-compatible API, LAN web UI, translation worker |
| `translation-connector` | `connector` | Receives Paperless workflow webhooks; adds linked English companions |

## Endpoint

`https://translation.<domainname_infra>` (internal only). Web UI at `/`, API at
`/v2/...`. API keys: `composition_translation_server_api_keys` (name → key);
send `Authorization: DeepL-Auth-Key <key>`.

## Paperless

The role creates, through the Paperless API:

- tags `auto-translated` (companions), `translation-failed`, `translate` (add it to
  a document to translate it again);
- the `translation` Document Link custom field;
- the workflow **Translate to English**: on *Document added* (not companions) and
  on *Document updated* with the `translate` tag, a webhook to the connector.

The workflow is created once. To change it, edit or delete it in Paperless and
re-run the role.

The connector uses the Paperless admin token (`vault_paperless_ngx_api_token`):
Paperless permissions are per object, so a limited user could not see every
owner's documents. Companions copy the original's owner and permissions.

Backfill existing documents:

```bash
ssh storage 'docker exec translation-connector translation-server connector backfill --since 2026-01-01 --dry-run'
ssh storage 'docker exec translation-connector translation-server connector backfill --since 2026-01-01'
```

## Key variables

| Variable | Default | Description |
| --- | --- | --- |
| `composition_translation_server_image` | `ghcr.io/awfulwoman/translation-server:latest` | Pulled on every run; pin `sha-<short>` to roll back |
| `composition_translation_server_backends` | local translategemma:4b, cloud gemma4:31b-cloud | Backends offered; `default` is used by Paperless |
| `composition_translation_server_source_langs` | `[DE]` | Paperless documents in these languages are translated |
| `composition_translation_server_target_lang` | `EN-GB` | |
| `composition_translation_server_add_note` | `false` | Also add the English text as a note on the original |
| `composition_translation_server_connector_enabled` | `true` | |

Vault: `vault_composition_translation_server_paperless_key` (the connector's API
key), `vault_composition_translation_server_webhook_secret` (Paperless → connector).

## Data

`config/data` (jobs, expire after 72 h; segment cache) and `config/connector`
(queue state). ZFS policy `low`: nothing here cannot be rebuilt.

## Deploy

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags composition -e target_composition=translation-server
```
