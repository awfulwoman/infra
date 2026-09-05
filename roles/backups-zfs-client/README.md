# ZFS Backup - Client

Use this role on hosts that need ZFS backups. It starts regular snapshots of the ZFS filesystem. It then installs a ZFS user, so that the backup server can connect over SSH and tell the client to send its ZFS dataset snapshots.

This is a pull strategy, not a push strategy. The client itself never has access to the backup server. This lowers the risk of island-hopping attacks.
