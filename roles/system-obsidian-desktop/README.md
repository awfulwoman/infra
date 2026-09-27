# system-obsidian-desktop

This role installs the Obsidian desktop app on macOS and keeps it running in
the logged-in GUI session, through a LaunchAgent with `KeepAlive`.

On Malcolm, this app is the only link to Obsidian Sync, which carries vaults to
the iPhone. Every other host gets vaults through Syncthing (see
[`system-syncthing-config`](../system-syncthing-config)). The app opens the
vaults straight from Malcolm's Syncthing folders, so edits flow both ways:

```
iPhone ⇄ Obsidian Sync ⇄ Obsidian (Malcolm) ⇄ ~/Syncthing/Obsidian/<vault> ⇄ Syncthing ⇄ storage, agatha
```

## One-off manual setup

Do this over Screen Sharing on Malcolm. Sync login can't be automated because
of MFA and a GUI-only flow.

1. Open Obsidian and log in to your Obsidian account (Settings → General).
2. For each vault (**Charlie**, **AgentMemory**):
   1. Open folder as vault: `~/Syncthing/Obsidian/<vault>`.
   2. Settings → Sync → connect it to the remote vault of the same name. The
      E2E password is `vault_obsidian_vault_key`.
   3. Keep every file type selected. Leave workspace files out of sync.

If a Syncthing folder is still empty when you connect it, Obsidian Sync
downloads the whole vault into it. Syncthing then spreads the vault to the
other hosts.

## Caveats

- Two sync engines share these folders. Syncthing ignores
  `.obsidian/workspace*.json` and `.trash`, so the busiest per-device files
  don't bounce between them.
- Any `.sync-conflict-*` file Syncthing creates is an ordinary file to
  Obsidian Sync, so it reaches the phone too.
- The app only syncs while a GUI session exists. Malcolm auto-logs in as the
  admin user.
