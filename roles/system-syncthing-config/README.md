# system-syncthing-config

This role configures every managed Syncthing instance declaratively from one
place. It runs on camina, the control node, and reaches each instance over its
REST API. It installs nothing: `composition-syncthing` (Linux, in a container)
and `system-syncthing-macos` (native) run the daemons.

## What it does

1. **Discover.** It reads the device ID of each host named in
   `syncthing_folders` from `/rest/system/status`. IDs are never recorded in
   inventory, so a rebuilt instance gets re-paired on the next run.
2. **Derive.** It works out each host's devices, folders and ignore patterns
   with the `syncthing_host_config` filter
   (`plugins/filters/syncthing_config.py`). Peers get an explicit
   `tcp://<host_ipv4>:22000` address, because container instances can't rely on
   local discovery.
3. **Apply.** It upserts each device and folder. It starts from the live
   object, or from Syncthing's defaults for a new one, overlays the declared
   fields, and does a `PUT` only when that changes something. It sets ignore
   patterns through `/rest/db/ignores`. A `.stignore` file isn't synced, so each
   member sets its own.
4. **Secure.** It sets the web UI login on every instance.
5. **Restart.** It restarts an instance if the API reports that a restart is
   required.

It only touches objects that are declared. Devices and folders added by hand,
such as storage's Misc, Memes and Screenshots shared with a laptop, are left
alone.

## Reaching instances

| Instance | Default endpoint |
|---|---|
| Container (`composition-syncthing`) | `https://syncthing-<host_name>.<domainname_infra>`, through that host's Traefik |
| Native (`system-syncthing-macos`) | set in host_vars: Syncthing's own self-signed HTTPS on `:8384` |

## Variables

| Variable | Where | Description |
|---|---|---|
| `syncthing_folders` | `group_vars/infra/core.yaml` | Folder list: `id`, `label`, `path`, `hosts`, `ignores`, optional `rescan_interval` (seconds; omitted = leave Syncthing's own value) |
| `syncthing_api_key` | `vault_syncthing_api_key` | Shared key; each daemon gets it as `STGUIAPIKEY` |
| `syncthing_gui_user` / `syncthing_gui_password` | defaults / vault | Web UI login |
| `syncthing_api_url` | instance host_vars | Overrides the Traefik endpoint |
| `syncthing_api_validate_certs` | instance host_vars | `false` for a self-signed endpoint |
| `syncthing_folder_root` | instance host_vars | The root Syncthing sees for folder paths (default `/var/syncthing`) |

## Adding a host

Deploy Syncthing on the host, add it to the `hosts` of each folder it should
hold, then run camina with `--tags system-syncthing-config`.
