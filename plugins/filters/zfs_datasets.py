#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Derive dataset lists from a host's declarative `zfs:` structure.

The pure logic (resolve_datasets and the selectors built on it) has no
dependency on Ansible, so it can be unit tested directly; FilterModule is the
thin Ansible-facing adapter.

A dataset's policy answers three separate questions, so every filter here must
resolve policy the same way:

    none      no snapshots, so no replication is possible
    low       snapshots kept locally only
    high      also pulled to the backup server
    critical  also pushed off-site

Policy is either stated on the dataset or inherited from a parent that sets
`children_inherit_policy`. Selecting on the stated value alone would make
replication disagree with retention about what a dataset's policy is.
"""

# Policies that earn a copy on the backup server.
BACKUP_POLICIES = ('high', 'critical')

# Policies that earn a copy off-site.
OFFSITE_POLICIES = ('critical',)


def resolve_datasets(zfs_dict):
    """Walk a `zfs:` structure and return every dataset with its policy resolved.

    Each item is a dictionary with:
      - dataset: full dataset path
      - policy: resolved policy, after inheritance ('none' if never set)
      - properties: dataset properties, if any
      - delegation: delegation settings, if any
      - snapshots_discover_children: True when runtime child discovery is on
    """
    if not isinstance(zfs_dict, dict):
        raise TypeError('resolve_datasets requires a dictionary')

    result = []
    _walk(zfs_dict, result, [], None)
    return result


def _walk(current, result, path, inherited_policy):
    if not isinstance(current, dict):
        return

    for key, value in current.items():
        if key == 'datasets' and isinstance(value, dict):
            for name, config in value.items():
                _visit(name, config, result, path, inherited_policy)
        elif isinstance(value, dict):
            # A pool introduces a new path component; anything else is a
            # container key (properties, vdevs, ...) that we walk through.
            next_path = path + [key] if 'datasets' in value else path
            _walk(value, result, next_path, inherited_policy)


def _visit(name, config, result, path, inherited_policy):
    dataset_path = path + [name]
    config = config if isinstance(config, dict) else {}
    states_own_policy = 'policy' in config

    if states_own_policy:
        policy = config['policy']
    elif inherited_policy is not None:
        policy = inherited_policy
    else:
        policy = 'none'

    record = {
        'dataset': '/'.join(dataset_path),
        'policy': policy,
    }

    for field in ('properties', 'delegation'):
        value = config.get(field)
        if isinstance(value, dict) and value:
            record[field] = value

    if config.get('snapshots_discover_children', False):
        record['snapshots_discover_children'] = True

    result.append(record)

    # Work out what, if anything, flows down to the children.
    #
    # A dataset that sets `children_inherit_policy` starts a fresh chain from
    # its own policy. Otherwise an existing chain continues, unless this
    # dataset stated a policy of its own, which breaks it.
    if config.get('children_inherit_policy', False):
        child_inherited = policy
    elif inherited_policy is not None and not states_own_policy:
        child_inherited = inherited_policy
    else:
        child_inherited = None

    _walk(config, result, dataset_path, child_inherited)


def _select(zfs_dict, policies):
    """Return datasets whose resolved policy is one of `policies`."""
    selected = []
    for record in resolve_datasets(zfs_dict):
        if record['policy'] not in policies:
            continue
        entry = {'dataset': record['dataset']}
        for field in ('properties', 'delegation'):
            if field in record:
                entry[field] = record[field]
        selected.append(entry)
    return selected


def backup_datasets(zfs_dict):
    """Datasets the backup server pulls: policy high or critical."""
    return _select(zfs_dict, BACKUP_POLICIES)


def offsite_datasets(zfs_dict):
    """Datasets replicated off-site: policy critical."""
    return _select(zfs_dict, OFFSITE_POLICIES)


def all_datasets(zfs_dict):
    """Every dataset path, in declaration order."""
    return [record['dataset'] for record in resolve_datasets(zfs_dict)]


def all_pools(zfs_dict):
    """Top-level pool names."""
    if not isinstance(zfs_dict, dict):
        raise TypeError('all_pools requires a dictionary')

    return [
        key
        for key, value in zfs_dict.items()
        if isinstance(value, dict) and 'datasets' in value
    ]


def datasets_with_config(zfs_dict):
    """Every dataset with its properties and delegation, policy omitted."""
    result = []
    for record in resolve_datasets(zfs_dict):
        entry = {'dataset': record['dataset']}
        for field in ('properties', 'delegation'):
            if field in record:
                entry[field] = record[field]
        result.append(entry)
    return result


def datasets_with_policy(zfs_dict):
    """Every dataset with its resolved policy and discovery flag."""
    result = []
    for record in resolve_datasets(zfs_dict):
        entry = {'dataset': record['dataset'], 'policy': record['policy']}
        if 'snapshots_discover_children' in record:
            entry['snapshots_discover_children'] = True
        result.append(entry)
    return result


class FilterModule(object):
    """Custom filters for ZFS dataset processing"""

    def filters(self):
        return {
            'zfs_all_datasets': self.zfs_all_datasets,
            'zfs_all_pools': self.zfs_all_pools,
            'zfs_datasets_with_config': self.zfs_datasets_with_config,
            'zfs_critical_datasets': self.zfs_critical_datasets,
            'zfs_backup_datasets': self.zfs_backup_datasets,
            'zfs_offsite_datasets': self.zfs_offsite_datasets,
            'zfs_datasets_with_policy': self.zfs_datasets_with_policy,
        }

    @staticmethod
    def _guard(func, zfs_dict, name):
        try:
            return func(zfs_dict)
        except TypeError:
            from ansible.errors import AnsibleFilterError

            raise AnsibleFilterError('%s requires a dictionary' % name)

    def zfs_all_datasets(self, zfs_dict):
        return self._guard(all_datasets, zfs_dict, 'zfs_all_datasets')

    def zfs_all_pools(self, zfs_dict):
        return self._guard(all_pools, zfs_dict, 'zfs_all_pools')

    def zfs_datasets_with_config(self, zfs_dict):
        return self._guard(datasets_with_config, zfs_dict, 'zfs_datasets_with_config')

    def zfs_critical_datasets(self, zfs_dict):
        return self._guard(offsite_datasets, zfs_dict, 'zfs_critical_datasets')

    def zfs_backup_datasets(self, zfs_dict):
        return self._guard(backup_datasets, zfs_dict, 'zfs_backup_datasets')

    def zfs_offsite_datasets(self, zfs_dict):
        return self._guard(offsite_datasets, zfs_dict, 'zfs_offsite_datasets')

    def zfs_datasets_with_policy(self, zfs_dict):
        return self._guard(datasets_with_policy, zfs_dict, 'zfs_datasets_with_policy')
