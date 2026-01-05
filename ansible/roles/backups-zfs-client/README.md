# ZFS Backup - Client

This role is used on hosts that require ZFS backups. It installs Sanoid, and initiates regular snapshots of the ZFS filesystem. It then ensures that a ZFS user is installed that allows access via the backup server (via SSH) that will then command the client to send existing ZFS dataset snapshots to the backup server.

Note that this is a pull strategy rather than a push strategy. This ensures that the client server itself never has access to the backup server, lessing the risk of island hopping attacks.
