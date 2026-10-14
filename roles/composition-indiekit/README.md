# composition-indiekit

[Indiekit](https://github.com/getindiekit/indiekit): a Micropub/IndieAuth server
that publishes posts to awfulwoman.com by committing Markdown to
`awfulwoman/awfulwoman.com` on `main`. The existing GitHub Actions build then
deploys the site.

Endpoint: `https://indie.{{ domainname_infra }}` (Tailscale only, never public).
The IndieAuth identity is `https://awfulwoman.com`; the site `<head>` must link
to this endpoint (`micropub`, `authorization_endpoint`, `token_endpoint`).

## Variables

| Variable | Purpose |
| --- | --- |
| `composition_indiekit_image` | Pinned image. Unverified at draft time. |
| `composition_indiekit_publication_url` | Site URL (IndieAuth `me`). |
| `vault_composition_indiekit_secret` | Signs tokens. |
| `vault_composition_indiekit_password_secret` | Login password hash (see below). |
| `vault_composition_indiekit_github_token` | Fine-grained PAT, contents:write on the site repo only. |

## First deploy

1. Deploy with no `password_secret`.
2. Visit `/auth/new-password`, set a password, copy the hash.
3. Vault it as `vault_composition_indiekit_password_secret`, redeploy.
   Hashes contain `$`; the env template single-quotes it.

## Data

`config/mongo` holds tokens and post metadata. Posts themselves live in git.
Mongo sits on an internal network without auth.

## Gotchas

- Post paths in `indiekit.config.js.j2` are a best guess at the Hugo layout;
  check the first published post of each type.
- EXIF: API commits bypass the site's `exif.sh` pre-commit hook.
