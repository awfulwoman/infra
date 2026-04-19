# system-nvm

Installs [nvm](https://github.com/nvm-sh/nvm) and a specified Node.js version for the Ansible user. Downloads the nvm install script, installs the configured Node version, and optionally sets it as the `nvm` default alias. Idempotent — skips installation steps if nvm and the requested Node version are already present.
