# certbot

<img width="404" height="799" alt="image" src="https://github.com/user-attachments/assets/3d52224f-4850-48f9-8327-2a1033803dbc" align="right" width="50px"/>
Not _really_ certbot. More a bunch of Ansible roles strung together to mimic some of the functionality of the [real certbot](https://certbot.eff.org/).

Because it's used purely for internal network certs - and needs to handle wildcards - it only makes use of [DNS-01 challenges](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).

The certs are downloaded to the host and require another role to distribute them elsewhere."
