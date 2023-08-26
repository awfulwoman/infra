#!/usr/bin/python
def zfs_path(a):
    ''' transforms a zfs object to a path '''
    return "Banana"

class FilterModule(object):
    def filters(self):
        return {
            'zfs_path': zfs_path
        }
