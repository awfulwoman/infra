#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.errors import AnsibleFilterError


class FilterModule(object):
    """Custom filters for ZFS dataset processing"""

    def filters(self):
        return {
            'zfs_all_datasets': self.zfs_all_datasets,
            'zfs_all_pools': self.zfs_all_pools,
            'zfs_datasets_with_config': self.zfs_datasets_with_config,
            'zfs_critical_datasets': self.zfs_critical_datasets,
            'zfs_backup_datasets': self.zfs_backup_datasets,
            'zfs_datasets_with_importance': self.zfs_datasets_with_importance,
        }

    def zfs_all_datasets(self, zfs_dict):
        """
        Extract all dataset paths from a ZFS configuration dictionary.
        """
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_all_datasets requires a dictionary')

        result = []
        self._walk_tree(zfs_dict, result, [])
        return result

    def zfs_all_pools(self, zfs_dict):
        """
        Extract all top-level pool names from a ZFS configuration dictionary.
        """
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_all_pools requires a dictionary')

        pools = []

        for key, value in zfs_dict.items():
            if isinstance(value, dict) and 'datasets' in value:
                pools.append(key)

        return pools

    def zfs_datasets_with_config(self, zfs_dict):
        """
        Extract all datasets with their properties and delegation configuration.

        Returns an array where each item is a dictionary containing:
        - dataset: The full dataset path (string)
        - properties: Dictionary of properties (optional, only if exists)
        - delegation: Dictionary of delegation settings (optional, only if exists)
        """
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_datasets_with_config requires a dictionary')

        result = []
        self._walk_tree_with_config(zfs_dict, result, [])
        return result

    def _walk_tree(self, current_dict, result, path_components):
        """
        Recursively walk the dictionary tree to find all datasets.
        """
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

    def _walk_tree_with_config(self, current_dict, result, path_components):
        """
        Recursively walk the dictionary tree to find all datasets with their config.
        """
        if not isinstance(current_dict, dict):
            return

        for key, value in current_dict.items():
            if key == 'datasets' and isinstance(value, dict):
                for dataset_name, dataset_value in value.items():
                    dataset_path = path_components + [dataset_name]

                    dataset_dict = {
                        'dataset': '/'.join(dataset_path)
                    }

                    if isinstance(dataset_value, dict) and 'properties' in dataset_value:
                        properties = dataset_value['properties']
                        if isinstance(properties, dict) and properties:
                            dataset_dict['properties'] = properties

                    if isinstance(dataset_value, dict) and 'delegation' in dataset_value:
                        delegation = dataset_value['delegation']
                        if isinstance(delegation, dict) and delegation:
                            dataset_dict['delegation'] = delegation

                    result.append(dataset_dict)

                    if isinstance(dataset_value, dict):
                        self._walk_tree_with_config(dataset_value, result, dataset_path)
            elif isinstance(value, dict):
                if 'datasets' in value:
                    self._walk_tree_with_config(value, result, path_components + [key])
                else:
                    self._walk_tree_with_config(value, result, path_components)

    def zfs_critical_datasets(self, zfs_dict):
        """
        Extract all datasets marked as 'critical' from a ZFS configuration dictionary.

        Processes the zfs dictionary and extracts all datasets that have importance: critical.

        Args:
            zfs_dict: ZFS configuration dictionary

        """
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_critical_datasets requires a dictionary')

        result = []
        self._extract_critical_datasets(zfs_dict, result, [])
        return result

    def _extract_critical_datasets(self, current_dict, result, path_components):
        """
        Recursively extract datasets marked as critical.
        """
        if not isinstance(current_dict, dict):
            return

        for key, value in current_dict.items():
            if key == 'datasets' and isinstance(value, dict):
                # Found a 'datasets' key - check each dataset
                for dataset_name, dataset_value in value.items():
                    dataset_path = path_components + [dataset_name]

                    # Check if this dataset is marked as critical
                    is_critical = False
                    if isinstance(dataset_value, dict) and 'importance' in dataset_value:
                        if dataset_value['importance'] == 'critical':
                            is_critical = True

                    if is_critical:
                        # Build the dataset dictionary
                        dataset_dict = {
                            'dataset': '/'.join(dataset_path)
                        }

                        # Extract properties if they exist
                        if 'properties' in dataset_value:
                            properties = dataset_value['properties']
                            if isinstance(properties, dict) and properties:
                                dataset_dict['properties'] = properties

                        # Extract delegation if it exists
                        if 'delegation' in dataset_value:
                            delegation = dataset_value['delegation']
                            if isinstance(delegation, dict) and delegation:
                                dataset_dict['delegation'] = delegation

                        result.append(dataset_dict)

                    # Recurse into nested datasets
                    if isinstance(dataset_value, dict):
                        self._extract_critical_datasets(dataset_value, result, dataset_path)
            elif isinstance(value, dict):
                # Check if this is a pool
                if 'datasets' in value:
                    self._extract_critical_datasets(value, result, path_components + [key])
                else:
                    self._extract_critical_datasets(value, result, path_components)

    def zfs_backup_datasets(self, zfs_dict):
        """
        Extract all datasets marked for backup from a ZFS configuration dictionary.

        Returns datasets that have importance: high or importance: critical.

        Args:
            zfs_dict: ZFS configuration dictionary
        """
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_backup_datasets requires a dictionary')

        result = []
        self._extract_backup_datasets(zfs_dict, result, [])
        return result

    def _extract_backup_datasets(self, current_dict, result, path_components):
        """
        Recursively extract datasets marked as high or critical importance.
        """
        if not isinstance(current_dict, dict):
            return

        for key, value in current_dict.items():
            if key == 'datasets' and isinstance(value, dict):
                for dataset_name, dataset_value in value.items():
                    dataset_path = path_components + [dataset_name]

                    # Check if this dataset is marked as high or critical
                    should_backup = False
                    if isinstance(dataset_value, dict) and 'importance' in dataset_value:
                        if dataset_value['importance'] in ('high', 'critical'):
                            should_backup = True

                    if should_backup:
                        dataset_dict = {
                            'dataset': '/'.join(dataset_path)
                        }

                        if 'properties' in dataset_value:
                            properties = dataset_value['properties']
                            if isinstance(properties, dict) and properties:
                                dataset_dict['properties'] = properties

                        if 'delegation' in dataset_value:
                            delegation = dataset_value['delegation']
                            if isinstance(delegation, dict) and delegation:
                                dataset_dict['delegation'] = delegation

                        result.append(dataset_dict)

                    if isinstance(dataset_value, dict):
                        self._extract_backup_datasets(dataset_value, result, dataset_path)
            elif isinstance(value, dict):
                if 'datasets' in value:
                    self._extract_backup_datasets(value, result, path_components + [key])
                else:
                    self._extract_backup_datasets(value, result, path_components)

    def zfs_datasets_with_importance(self, zfs_dict):
        """
        Extract all datasets with their importance level.

        Returns an array where each item is a dictionary containing:
        - dataset: The full dataset path (string)
        - importance: The importance level (string, defaults to 'none')

        Args:
            zfs_dict: ZFS configuration dictionary
        """
        if not isinstance(zfs_dict, dict):
            raise AnsibleFilterError('zfs_datasets_with_importance requires a dictionary')

        result = []
        self._walk_tree_with_importance(zfs_dict, result, [])
        return result

    def _walk_tree_with_importance(self, current_dict, result, path_components):
        """
        Recursively walk the dictionary tree to find all datasets with their importance.
        """
        if not isinstance(current_dict, dict):
            return

        for key, value in current_dict.items():
            if key == 'datasets' and isinstance(value, dict):
                for dataset_name, dataset_value in value.items():
                    dataset_path = path_components + [dataset_name]

                    # Extract importance, defaulting to 'none'
                    importance = 'none'
                    if isinstance(dataset_value, dict) and 'importance' in dataset_value:
                        importance = dataset_value['importance']

                    dataset_dict = {
                        'dataset': '/'.join(dataset_path),
                        'importance': importance,
                    }

                    result.append(dataset_dict)

                    if isinstance(dataset_value, dict):
                        self._walk_tree_with_importance(dataset_value, result, dataset_path)
            elif isinstance(value, dict):
                if 'datasets' in value:
                    self._walk_tree_with_importance(value, result, path_components + [key])
                else:
                    self._walk_tree_with_importance(value, result, path_components)
