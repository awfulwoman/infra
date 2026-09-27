import pytest

from syncthing_config import syncthing_host_config

STORAGE = "server-64gb-storage"
MALCOLM = "apple-macmini-m4-16gb-malcolm"
AGATHA = "minipc-8gb-agatha"

PEERS = {
    STORAGE: {"device_id": "STORAGE-ID", "address": "192.168.1.116"},
    MALCOLM: {"device_id": "MALCOLM-ID", "address": "192.168.1.99"},
    AGATHA: {"device_id": "AGATHA-ID", "address": "192.168.1.176"},
}

CHARLIE = {
    "id": "obsidian-charlie",
    "label": "Obsidian: Charlie",
    "path": "Obsidian/Charlie",
    "hosts": [STORAGE, MALCOLM, AGATHA],
    "ignores": [".obsidian/workspace*.json", ".trash"],
}


def folder_device(device_id):
    return {"deviceID": device_id, "introducedBy": "", "encryptionPassword": ""}


def test_folder_path_is_joined_to_host_root_and_lists_every_member():
    result = syncthing_host_config([CHARLIE], PEERS, STORAGE, "/var/syncthing")

    assert result["folders"] == [
        {
            "id": "obsidian-charlie",
            "label": "Obsidian: Charlie",
            "path": "/var/syncthing/Obsidian/Charlie",
            "type": "sendreceive",
            "fsWatcherEnabled": True,
            "devices": [
                folder_device("STORAGE-ID"),
                folder_device("MALCOLM-ID"),
                folder_device("AGATHA-ID"),
            ],
        }
    ]


def test_devices_are_the_other_members_with_explicit_lan_address():
    result = syncthing_host_config([CHARLIE], PEERS, STORAGE, "/var/syncthing")

    assert result["devices"] == [
        {
            "deviceID": "MALCOLM-ID",
            "name": MALCOLM,
            "addresses": ["tcp://192.168.1.99:22000", "dynamic"],
            "autoAcceptFolders": False,
        },
        {
            "deviceID": "AGATHA-ID",
            "name": AGATHA,
            "addresses": ["tcp://192.168.1.176:22000", "dynamic"],
            "autoAcceptFolders": False,
        },
    ]


def test_ignores_are_keyed_by_folder_id():
    result = syncthing_host_config([CHARLIE], PEERS, STORAGE, "/var/syncthing")

    assert result["ignores"] == {
        "obsidian-charlie": [".obsidian/workspace*.json", ".trash"],
    }


def test_folder_without_ignores_gets_an_empty_list():
    folder = {k: v for k, v in CHARLIE.items() if k != "ignores"}

    result = syncthing_host_config([folder], PEERS, STORAGE, "/var/syncthing")

    assert result["ignores"] == {"obsidian-charlie": []}


def test_folders_this_host_is_not_in_are_skipped():
    other = dict(CHARLIE, id="other", hosts=[MALCOLM, AGATHA])

    result = syncthing_host_config([other], PEERS, STORAGE, "/var/syncthing")

    assert result == {"folders": [], "devices": [], "ignores": {}}


def test_device_shared_by_several_folders_is_listed_once():
    memory = dict(CHARLIE, id="obsidian-agentmemory", path="Obsidian/AgentMemory")

    result = syncthing_host_config([CHARLIE, memory], PEERS, STORAGE, "/var/syncthing")

    assert [d["deviceID"] for d in result["devices"]] == ["MALCOLM-ID", "AGATHA-ID"]


def test_peer_without_address_relies_on_discovery():
    peers = dict(PEERS, **{MALCOLM: {"device_id": "MALCOLM-ID", "address": ""}})

    result = syncthing_host_config([CHARLIE], peers, STORAGE, "/var/syncthing")

    assert result["devices"][0]["addresses"] == ["dynamic"]


def test_trailing_slash_on_root_is_not_doubled():
    result = syncthing_host_config([CHARLIE], PEERS, STORAGE, "/var/syncthing/")

    assert result["folders"][0]["path"] == "/var/syncthing/Obsidian/Charlie"


def test_duplicate_folder_ids_are_rejected():
    with pytest.raises(ValueError, match="obsidian-charlie"):
        syncthing_host_config([CHARLIE, CHARLIE], PEERS, STORAGE, "/var/syncthing")


def test_member_host_missing_from_peers_is_rejected():
    folder = dict(CHARLIE, hosts=[STORAGE, "no-such-host"])

    with pytest.raises(ValueError, match="no-such-host"):
        syncthing_host_config([folder], PEERS, STORAGE, "/var/syncthing")
