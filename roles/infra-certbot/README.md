# certbot

<img width="140" alt="image" src="https://github.com/user-attachments/assets/3d52224f-4850-48f9-8327-2a1033803dbc" align="right" width="10px" />

This is not _really_ certbot. It is a set of Ansible roles joined to copy some of the function of the [real certbot](https://certbot.eff.org/).

This role uses internal network certs only, and it must handle wildcards. For this reason, it uses only [DNS-01 challenges](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).

The role downloads the certs to the host. A separate role is needed to distribute them elsewhere.

A domain entry in `infra_certbot_domains` can set `distribute: true`. This copies its newest fullchain and private key into `infra_certbot_distribution_dir` on every run, so the role heals itself if that directory is ever wiped or falls out of sync. This write is local and atomic; the role touches nothing outside the host. Serving that directory to other hosts is out of scope for this role.
