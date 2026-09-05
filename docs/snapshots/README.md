# Domain snapshots

A reproducible before/after record of how every registered service name
resolves and serves TLS, captured from two vantages:

- **LAN** — run from a machine on the home network.
- **Remote** — run from `public01` (Hetzner), standing in for a phone on
  cellular.

Two vantages matter, because split-horizon DNS means the same name can
resolve differently, depending on where the query comes from. A name that
works from the LAN can be dead from outside it, and the reverse can also
be true.

## Capturing a snapshot

```bash
scripts/snapshot-domains.sh
```

This derives the current list of registered service names from inventory
(`playbooks/utility/export-service-names.yaml`). It then runs
`scripts/snapshot-domains.py` locally (LAN) and over SSH on `public01`
(remote), and writes:

- `docs/snapshots/domains-lan.json`
- `docs/snapshots/domains-remote.json`

Each entry per service name records the CNAME chain, resolved IP(s), HTTPS
status code, and served certificate's subject/issuer/expiry. Output is
sorted-key JSON with no volatile fields (no timestamps), so two runs against
unchanged infrastructure diff cleanly — `git diff -- docs/snapshots` shows
only what actually changed.

## The baseline

`domains-lan.json` and `domains-remote.json` in this directory are the
baseline captured before the centralized-wildcard-TLS / derived-CNAME-DNS
redesign (#262). Re-run the script, and diff against these files, to prove
that a change has not broken a working name, and that only the intended
changes appear.
