# awfulwoman.com

This role serves the [awfulwoman.com](https://awfulwoman.com) personal website through an nginx container. A dedicated deploy user, with an SSH public key, deploys the site content separately into a shared directory on the host. This role provisions the nginx container, its config, and the OS users and groups that this setup needs.

The container handles multiple hostnames: the primary personal domain, plus two legacy domains, all with Let's Encrypt TLS through Traefik.

## Key Variables

| Variable | Purpose |
|----------|---------|
| `awfulwoman_sites_base` | Base path for site content on the host (default: `/fastpool/sites`) |
| `awfulwoman_path` | Full path to the site content directory |
| `awfulwoman_deploy_user` | OS user that CI/CD deploys content as (`vault_sitedeployer_user`) |
| `awfulwoman_deploy_group` | Shared group between the deploy user and the nginx container user (default: `nginx`) |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ awfulwoman_path }}` | Site HTML content root |
| `{{ composition_config }}/nginx.conf` | Custom nginx configuration |

## Integrations

- **Traefik**: Routes `{{ domainname_personal }}`, `{{ vault_domainname_wc }}`, and `{{ vault_domainname_se }}` to the container, with Let's Encrypt TLS.
- **Deploy user**: A separate system user (`vault_sitedeployer_user`), with an authorized SSH key, deploys content to `awfulwoman_path`. Both the deploy user and the Ansible user belong to the `nginx` group, for shared directory access.

## Notes

The role adds a default `index.html` when none exists, so the site is never empty after the first deployment.
