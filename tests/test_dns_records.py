import pytest

from dns_records import DuplicateLabelError, derive_dns_records


def test_fixed_single_host_service():
    hosts = {
        "minipc-8gb-homebrain": {
            "fqdn": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.130",
            "compositions": ["gitea"],
        },
    }
    compositions = {"gitea": ["gitea"]}

    result = derive_dns_records(hosts, compositions)

    assert result == {
        "a_records": {
            "minipc-8gb-homebrain": {
                "name": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
                "target": "100.80.1.130",
            },
        },
        "cnames": {
            "gitea": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
        },
    }


def test_per_host_label_derived_from_host_name():
    hosts = {
        "minipc-8gb-homebrain": {
            "fqdn": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.130",
            "compositions": ["zfs-api"],
        },
        "server-64gb-storage": {
            "fqdn": "server-64gb-storage.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.116",
            "compositions": ["zfs-api"],
        },
    }
    compositions = {"zfs-api": ["zfs-api.{host}"]}

    result = derive_dns_records(hosts, compositions)

    assert result["cnames"] == {
        "zfs-api.minipc-8gb-homebrain": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
        "zfs-api.server-64gb-storage": "server-64gb-storage.xberg.ber.ewwww.eu",
    }


def test_per_host_label_override():
    hosts = {
        "server-64gb-storage": {
            "fqdn": "server-64gb-storage.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.116",
            "compositions": [
                {"composition": "jellyfin", "labels": ["media"]},
            ],
        },
    }
    compositions = {"jellyfin": ["jellyfin", "jellyfin-vue"]}

    result = derive_dns_records(hosts, compositions)

    assert result["cnames"] == {
        "media": "server-64gb-storage.xberg.ber.ewwww.eu",
    }


def test_two_instances_of_one_composition_on_one_host():
    hosts = {
        "minipc-8gb-homebrain": {
            "fqdn": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.130",
            "compositions": [
                {"composition": "syncthing", "name": "personal", "labels": ["sync-personal"]},
                {"composition": "syncthing", "name": "shared", "labels": ["sync-shared"]},
            ],
        },
    }
    compositions = {"syncthing": ["syncthing"]}

    result = derive_dns_records(hosts, compositions)

    assert result["a_records"] == {
        "minipc-8gb-homebrain": {
            "name": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
            "target": "100.80.1.130",
        },
    }
    assert result["cnames"] == {
        "sync-personal": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
        "sync-shared": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
    }


def test_duplicate_label_across_hosts_raises_naming_composition_and_hosts():
    hosts = {
        "minipc-8gb-homebrain": {
            "fqdn": "minipc-8gb-homebrain.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.130",
            "compositions": ["gitea"],
        },
        "server-64gb-storage": {
            "fqdn": "server-64gb-storage.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.116",
            "compositions": ["gitea"],
        },
    }
    compositions = {"gitea": ["gitea"]}

    with pytest.raises(DuplicateLabelError) as exc_info:
        derive_dns_records(hosts, compositions)

    message = str(exc_info.value)
    assert "gitea" in message
    assert "minipc-8gb-homebrain" in message
    assert "server-64gb-storage" in message


def test_all_of_a_compositions_default_labels_are_derived():
    """jellyfin-vue is declared in composition_jellyfin_subdomains but is
    missing from server-64gb-storage's hand-maintained cnames list today
    (the drift #262 exists to fix). Once derivation is authoritative, both
    of the composition's declared labels must appear — neither can be
    silently dropped the way jellyfin-vue currently is.
    """
    hosts = {
        "server-64gb-storage": {
            "fqdn": "server-64gb-storage.xberg.ber.ewwww.eu",
            "tailscale_ipv4": "100.80.1.116",
            "compositions": ["jellyfin"],
        },
    }
    compositions = {"jellyfin": ["jellyfin", "jellyfin-vue"]}

    result = derive_dns_records(hosts, compositions)

    assert result["cnames"] == {
        "jellyfin": "server-64gb-storage.xberg.ber.ewwww.eu",
        "jellyfin-vue": "server-64gb-storage.xberg.ber.ewwww.eu",
    }
