#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Derive one host's Syncthing devices, folders and ignore patterns from the
inventory-wide `syncthing_folders` declaration. The output is shaped for the
Syncthing REST config API; FilterModule is the thin Ansible wrapper.
"""

SYNC_PORT = 22000


def _folder_device(device_id):
    return {"deviceID": device_id, "introducedBy": "", "encryptionPassword": ""}


def _device(host, peer):
    addresses = ["dynamic"]
    if peer.get("address"):
        addresses.insert(0, "tcp://%s:%d" % (peer["address"], SYNC_PORT))
    return {
        "deviceID": peer["device_id"],
        "name": host,
        "addresses": addresses,
        "autoAcceptFolders": False,
    }


def syncthing_host_config(folders, peers, this_host, folder_root):
    seen = set()
    for folder in folders:
        if folder["id"] in seen:
            raise ValueError("duplicate Syncthing folder id: %s" % folder["id"])
        seen.add(folder["id"])
        for host in folder["hosts"]:
            if host not in peers:
                raise ValueError(
                    "folder %s names %s, which has no Syncthing peer entry"
                    % (folder["id"], host)
                )

    root = folder_root.rstrip("/")
    result = {"folders": [], "devices": [], "ignores": {}}
    listed = set()

    for folder in folders:
        if this_host not in folder["hosts"]:
            continue
        members = folder["hosts"]
        result["folders"].append(
            {
                "id": folder["id"],
                "label": folder["label"],
                "path": "%s/%s" % (root, folder["path"].strip("/")),
                "type": "sendreceive",
                "fsWatcherEnabled": True,
                "devices": [
                    _folder_device(d)
                    for d in sorted(peers[h]["device_id"] for h in members)
                ],
            }
        )
        result["ignores"][folder["id"]] = list(folder.get("ignores", []))
        for host in members:
            if host != this_host and host not in listed:
                listed.add(host)
                result["devices"].append(_device(host, peers[host]))

    return result


class FilterModule(object):
    """Custom filters for declarative Syncthing configuration"""

    def filters(self):
        return {
            "syncthing_host_config": syncthing_host_config,
        }
