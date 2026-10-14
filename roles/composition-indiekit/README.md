# composition-indiekit

[Indiekit](https://github.com/getindiekit/indiekit): a Micropub/IndieAuth server
that publishes posts to awfulwoman.com by committing Markdown to
`awfulwoman/awfulwoman.com` on `main`. The existing GitHub Actions build then
deploys the site.

Endpoint: `https://indie.<personal domain>` (public; DNS CNAME in infra-public-resources).
The IndieAuth identity is `https://awfulwoman.com`; the site `<head>` must link
to this endpoint (`micropub`, `authorization_endpoint`, `token_endpoint`).

## Variables

| Variable | Purpose |
| --- | --- |
| `composition_indiekit_build_context` | Pinned upstream git commit to build. |
| `composition_indiekit_publication_url` | Site URL (IndieAuth `me`). |
| `vault_composition_indiekit_secret` | Signs tokens. |
| `vault_composition_indiekit_password_secret` | Login password hash (see below). |
| `vault_composition_indiekit_github_token` | Fine-grained PAT, contents:write on the site repo only. |

## Password

Set out of band: the bcrypt hash of the login password is vaulted as
`vault_composition_indiekit_password_secret`, and Traefik blocks
`/auth/new-password` so the web setup form is never exposed. To rotate, hash a
new password (`bcrypt`, cost 10), re-vault it, redeploy. Hashes contain `$`;
the env template single-quotes them.

## Image

Built from a pinned upstream commit (`composition_indiekit_build_context`);
no image is published upstream yet.

## Data

`config/mongo` holds tokens and post metadata. Posts themselves live in git.
Mongo sits on an internal network without auth.

## Gotchas

- Post paths in `indiekit.config.js.j2` are a best guess at the Hugo layout;
  check the first published post of each type.
- EXIF: API commits bypass the site's `exif.sh` pre-commit hook.
