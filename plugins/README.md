# Ansible Plugins

Custom Ansible plugins for this infrastructure.

## Filter Plugins

Located in `filters/`, these provide custom Jinja2 filters for use in playbooks and templates.

### `zfs_datasets.py`

Filters for processing the declarative `zfs` dictionary structure defined in host variables.

| Filter | Description |
|--------|-------------|
| `zfs_all_datasets` | Returns a list of all dataset paths |
| `zfs_all_pools` | Returns a list of top-level pool names |
| `zfs_datasets_with_config` | Returns datasets with their properties and delegation settings |
| `zfs_critical_datasets` | Returns datasets with `policy: critical` |
| `zfs_backup_datasets` | Returns datasets with `policy: high` or `critical` |
| `zfs_datasets_with_policy` | Returns all datasets with their policy level (supports inheritance) |

**Example usage:**

```yaml
# Get all dataset paths
- debug:
    msg: "{{ zfs | zfs_all_datasets }}"

# Get datasets that need backing up
- debug:
    msg: "{{ zfs | zfs_backup_datasets }}"
```
