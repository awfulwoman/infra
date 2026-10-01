# infra#297: deploy wiki-compiler and a password-protected wiki site

Infra side of `awfulwoman/wiki-compiler#1`. Unblocked now that wiki-compiler's
spec (milestones 1-7) is complete and its image publishes to
`ghcr.io/awfulwoman/wiki-compiler` on every push to `main`.

## Decisions

- **Vault name is `PersonalWiki`**, not `Wiki` as #297's task list drafted it
  (the user created the vault under this name on Malcolm). Every identifier
  below follows that: Syncthing folder id `obsidian-personalwiki`, label
  `Obsidian: PersonalWiki`, path `Obsidian/PersonalWiki`.
- **Gateway client token**: new `wiki` entry in
  `composition_gateway_server_auth_clients` → `vault_gateway_mcp_token_wiki`.
  Labels the compiler's calls in gateway's usage log, same as `gw-cli`/`hermes`.
- **Syncthing folder** `obsidian-personalwiki`: hosts `server-64gb-storage`
  (compiler writes here) and `apple-macmini-m4-16gb-malcolm` (desktop
  Obsidian, and the only link to Obsidian Sync for the phone). Not agatha or
  camina — nothing there needs it.
- **Obsidian Sync**: manual one-off on Malcolm, same as Charlie/AgentMemory
  (`roles/system-obsidian-desktop/README.md`). Add PersonalWiki as a third
  vault in that doc; the actual connect step stays a screen-share task, not
  something Ansible does.
- **`composition-wiki-compiler`** (new role, storage): pulls
  `ghcr.io/awfulwoman/wiki-compiler`. Mounts:
  - Charlie Syncthing folder, read-only → `NOTES_DIR`
  - PersonalWiki Syncthing folder, read-write → `OUTPUT_DIR`
  - a dedicated state dataset → `STATE_DIR`
  Env talks to gateway over the shared Docker network (`http://gateway:8000`,
  token above) and to Malcolm's Ollama for the model: reuses the existing
  `llm_default_ollama_base_url` / `llm_default_model` group vars (the model is
  already `gemma4:31b-cloud` — an Ollama Cloud model proxied through Malcolm's
  local Ollama — so "malcolm's Ollama" and "cloud model" are the same setting,
  not a choice between two). No DNS subdomain: it's reached by container name
  only, like mail-archive-server.
  - **`SOURCES` starts without `email`.** The PRD's own usage guard and the
    bulk-sender/noreply rules need a `filter-report` pass on a real sample
    before email backfills into the wiki; calendar/bookmarks/contacts/
    reminders/location carry no equivalent risk. Flip email on later as a
    separate, deliberate step.
  - **Budgets start small**: the Ollama Cloud account is metered and shared
    with the Hermes bots on agatha (#297's own constraint). Low
    `DAILY_CALL_BUDGET`/`DAILY_TOKEN_BUDGET` at first, raised after watching
    `wiki-compiler usage` for a few days.
- **`composition-wiki-site`** (new role, storage): no off-the-shelf image
  exists for Quartz, so this needs a small custom Dockerfile (Node, Quartz,
  build + serve). Content changes at most once an hour (the compiler's
  `RUN_INTERVAL_MINUTES` default), so a simple loop (rebuild, sleep, repeat)
  in the entrypoint is enough — no file-watcher needed. Serves the
  PersonalWiki folder read-only. Traefik basic auth, same pattern as
  `composition-basic-memory`: `vault_wiki_htpasswd` (bcrypt line for Traefik)
  / `vault_wiki_password` (plaintext, for the user). DNS subdomain `wiki`.
- **ZFS** on storage (`inventory/host_vars/server-64gb-storage/core.yaml`,
  under `compositions`): `wiki-compiler` dataset (state) → `policy: high`
  (not `critical` — rebuildable from the sources, just not free to redo);
  `wiki-site` dataset (build output) → `policy: none` (purely derived; the
  real content is the PersonalWiki Syncthing folder, already covered by the
  existing `syncthing: high` dataset).

## Not doing yet

- Flipping `email` on as a source — separate follow-up once a
  `filter-report` sample looks right.
- Backfilling before first deploy — let the scheduler's own cadence build up
  history; no one-shot bulk `--limit` run planned.

## Rollout

1. `composition-gateway`: add the `wiki` auth client entry; vault the token.
2. `inventory/group_vars/infra/core.yaml`: add the `obsidian-personalwiki`
   Syncthing folder.
3. New role `composition-wiki-compiler` + its ZFS dataset + host wiring on
   storage.
4. New role `composition-wiki-site` + its ZFS dataset + host wiring on
   storage.
5. `roles/system-obsidian-desktop/README.md`: document PersonalWiki as the
   third vault for the manual Obsidian Sync step.
6. Deploy `composition-gateway`, `composition-wiki-compiler`,
   `composition-wiki-site` to storage via `aw-deploy`; verify the compiler's
   `/health` and a real `/run`, then the wiki site behind basic auth.
7. Check off #297's task list and comment with what shipped vs. deferred
   (email source, Obsidian Sync manual step).
