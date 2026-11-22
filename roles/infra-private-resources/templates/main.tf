# No global pool - each VM gets its own pool from a directory under
# infra_privateresources_pool_path, which is a ZFS dataset.
# See vms.tf.j2 for per-VM pool definitions
