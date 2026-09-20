from zfs_datasets import backup_datasets, datasets_with_policy, offsite_datasets


def names(datasets):
    """Reduce filter output to a sorted list of dataset paths."""
    return sorted(d['dataset'] for d in datasets)


# ---------------------------------------------------------------------------
# Policy resolution must be identical across every filter.
#
# Three filters answer three questions about the same dataset tree:
#   zfs_datasets_with_policy -> what retention does it get?
#   zfs_backup_datasets      -> is it pulled to the backup server?
#   zfs_offsite_datasets     -> is it sent offsite?
#
# They must agree on what a dataset's policy *is*, however that policy was
# arrived at: stated outright, or inherited from a parent.
# ---------------------------------------------------------------------------


def test_explicit_policy_selects_for_backup():
    zfs = {
        'fastpool': {
            'datasets': {
                'compositions': {
                    'policy': 'low',
                    'datasets': {
                        'immich': {'policy': 'critical'},
                        'jellyfin': {'policy': 'low'},
                    },
                },
            },
        },
    }

    assert names(backup_datasets(zfs)) == ['fastpool/compositions/immich']


def test_inherited_policy_selects_for_backup():
    """A child inheriting 'critical' is backed up, exactly as if it said so."""
    zfs = {
        'fastpool': {
            'datasets': {
                'compositions': {
                    'policy': 'critical',
                    'children_inherit_policy': True,
                    'datasets': {
                        'immich': {},
                        'gatus': {'policy': 'low'},
                    },
                },
            },
        },
    }

    assert names(backup_datasets(zfs)) == [
        'fastpool/compositions',
        'fastpool/compositions/immich',
    ]


def test_inherited_policy_selects_for_offsite():
    zfs = {
        'fastpool': {
            'datasets': {
                'compositions': {
                    'policy': 'critical',
                    'children_inherit_policy': True,
                    'datasets': {
                        'paperless-ngx': {},
                    },
                },
            },
        },
    }

    assert 'fastpool/compositions/paperless-ngx' in names(offsite_datasets(zfs))


def test_inherited_low_policy_is_excluded_from_backup():
    """Inheritance must be able to exclude, not only include."""
    zfs = {
        'fastpool': {
            'datasets': {
                'compositions': {
                    'policy': 'low',
                    'children_inherit_policy': True,
                    'datasets': {
                        'jellyfin': {},
                        'logtide': {},
                    },
                },
            },
        },
    }

    assert backup_datasets(zfs) == []


def test_child_policy_breaks_the_inheritance_chain():
    """A stated policy stops the parent's value flowing further down."""
    zfs = {
        'fastpool': {
            'datasets': {
                'compositions': {
                    'policy': 'critical',
                    'children_inherit_policy': True,
                    'datasets': {
                        'immich': {
                            'policy': 'low',
                            'datasets': {'pgdata': {}},
                        },
                    },
                },
            },
        },
    }

    assert names(backup_datasets(zfs)) == ['fastpool/compositions']


def test_high_policy_is_backed_up_but_not_offsite():
    """The ladder: 'high' earns a second copy, 'critical' also earns a third."""
    zfs = {
        'fastpool': {
            'datasets': {
                'compositions': {
                    'policy': 'none',
                    'datasets': {
                        'freshrss': {'policy': 'high'},
                        'paperless-ngx': {'policy': 'critical'},
                    },
                },
            },
        },
    }

    assert names(backup_datasets(zfs)) == [
        'fastpool/compositions/freshrss',
        'fastpool/compositions/paperless-ngx',
    ]
    assert names(offsite_datasets(zfs)) == ['fastpool/compositions/paperless-ngx']


def test_undeclared_dataset_defaults_to_none():
    zfs = {
        'fastpool': {
            'datasets': {
                'scratch': {},
            },
        },
    }

    policies = {d['dataset']: d['policy'] for d in datasets_with_policy(zfs)}
    assert policies['fastpool/scratch'] == 'none'


def test_properties_are_carried_through_inheritance():
    """Encrypted datasets still need their properties when selected by inheritance."""
    zfs = {
        'slowpool': {
            'datasets': {
                'backups': {
                    'policy': 'critical',
                    'children_inherit_policy': True,
                    'datasets': {
                        'raw': {
                            'properties': {'encryption': 'aes-256-gcm'},
                        },
                    },
                },
            },
        },
    }

    raw = next(
        d for d in backup_datasets(zfs) if d['dataset'] == 'slowpool/backups/raw'
    )
    assert raw['properties'] == {'encryption': 'aes-256-gcm'}
