# Traefik Container

This container is used to provide reverse-proxy services via Traefik.

Most containers in this repo have labels in their `docker-compose.yaml` files that Traefik uses to control the routing for these containers.

The one exception is those containers (such as Home Assistant) that need to run in Host networking mode. Traefik is unable to control these containers as they sit outside the normal Docker netowrking stack. For those containers a providers file must be written and placed in the [providers directory](files/providers/) of Traefik. 

* [Traefik config](files/config.yaml)
* [Providers config](files/providers/)
* [Docker compose](templates/docker-compose.yaml.j2)
* [Container variables](vars/main.yaml)
