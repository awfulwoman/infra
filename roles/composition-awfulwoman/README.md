# awfulwoman.com

Serves the [awfulwoman.com](https://awfulwoman.com) personal website via an nginx container. The site content is deployed separately by a dedicated deploy user (via SSH public key) into a shared directory on the host; this role just provisions the nginx container, config, and the necessary OS users/groups to make that work.

The container handles multiple hostnames: the primary personal domain plus two legacy domains, all with Let's Encrypt TLS via Traefik.

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

- **Traefik**: Routes `{{ domainname_personal }}`, `{{ vault_domainname_wc }}`, and `{{ vault_domainname_se }}` to the container with Let's Encrypt TLS.
- **Deploy user**: A separate system user (`vault_sitedeployer_user`) with an authorised SSH key deploys content to `awfulwoman_path`. Both the deploy user and the Ansible user are added to the `nginx` group for shared directory access.

## Notes

A default `index.html` is placed if none exists, so the site is never empty after first deployment.
