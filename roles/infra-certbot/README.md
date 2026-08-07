# certbot

<img width="140" alt="image" src="https://github.com/user-attachments/assets/3d52224f-4850-48f9-8327-2a1033803dbc" align="right" width="10px" />

Not _really_ certbot. More a bunch of Ansible roles strung together to mimic some of the functionality of the [real certbot](https://certbot.eff.org/).

Because it's used purely for internal network certs - and needs to handle wildcards - it only makes use of [DNS-01 challenges](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).

The certs are downloaded to the host and require another role to distribute them elsewhere.

A domain entry in `infra_certbot_domains` can set `distribute: true` to have its newest fullchain + private key copied into `infra_certbot_distribution_dir` on every run (self-healing if that directory is ever wiped or falls out of sync). This is a purely local, atomic write — nothing outside the host is touched. Serving that directory to other hosts is out of scope for this role.
