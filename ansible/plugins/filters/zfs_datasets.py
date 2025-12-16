#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.errors import AnsibleFilterError


class FilterModule(object):
    """Custom filters for ZFS dataset processing"""

    def filters(self):
        return {
            'zfs_all_datasets': self.zfs_all_datasets,
        }

    def zfs_all_datasets(self, zfs_dict):
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_all_datasets requires a dictionary')
        
        result = []
        self._walk_tree(zfs_dict, result, [])
        return result

    def _walk_tree(self, current_dict, result, path_components):
        if not isinstance(current_dict, dict):
            return
        
        for key, value in current_dict.items():
            if key == 'datasets' and isinstance(value, dict):
                for dataset_name, dataset_value in value.items():
                    dataset_path = path_components + [dataset_name]
                    result.append('/'.join(dataset_path))
                    
                    if isinstance(dataset_value, dict):
                        self._walk_tree(dataset_value, result, dataset_path)
            elif isinstance(value, dict):
                if 'datasets' in value:
                    self._walk_tree(value, result, path_components + [key])
                else:
                    self._walk_tree(value, result, path_components)
