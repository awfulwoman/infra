#!/usr/bin/python
def zfs_path(a):
    ''' transforms a zfs object to a path '''
    return False

class FilterModule(object):
    def filters(self):
        return {
            'zfs_path': zfs_path
        }
