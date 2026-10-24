from dns_records import diff_public_records

ZONE = "ewwww.eu"
TTL = 300

DERIVED = {
    "a_records": {
        "server-64gb-storage": {
            "name": "server-64gb-storage.xberg.ber",
            "target": "100.80.1.116",
        },
    },
    "cnames": {
        "jellyfin": "server-64gb-storage.xberg.ber",
    },
}


def rrset(name, type_, value, ttl=TTL):
    return {"name": name, "type": type_, "ttl": ttl, "records": [{"value": value}]}


def in_sync():
    return [
        rrset("server-64gb-storage.xberg.ber", "A", "100.80.1.116"),
        rrset("jellyfin", "CNAME", "server-64gb-storage.xberg.ber.ewwww.eu."),
    ]


def test_empty_zone_publishes_everything():
    result = diff_public_records(DERIVED, [], ZONE, TTL)

    assert result == {
        "a_upserts": [{"name": "server-64gb-storage.xberg.ber", "value": "100.80.1.116"}],
        "a_deletes": [],
        "cname_upserts": [{"name": "jellyfin", "value": "server-64gb-storage.xberg.ber.ewwww.eu."}],
    }


def test_zone_already_in_sync_changes_nothing():
    result = diff_public_records(DERIVED, in_sync(), ZONE, TTL)

    assert result == {"a_upserts": [], "a_deletes": [], "cname_upserts": []}


def test_only_the_new_label_is_published():
    derived = {**DERIVED, "cnames": {**DERIVED["cnames"], "gitea": "server-64gb-storage.xberg.ber"}}

    result = diff_public_records(derived, in_sync(), ZONE, TTL)

    assert result["a_upserts"] == []
    assert result["cname_upserts"] == [{"name": "gitea", "value": "server-64gb-storage.xberg.ber.ewwww.eu."}]


def test_changed_host_ip_is_republished():
    existing = in_sync()
    existing[0] = rrset("server-64gb-storage.xberg.ber", "A", "100.80.1.1")

    result = diff_public_records(DERIVED, existing, ZONE, TTL)

    assert result["a_upserts"] == [{"name": "server-64gb-storage.xberg.ber", "value": "100.80.1.116"}]


def test_changed_ttl_is_republished():
    existing = in_sync()
    existing[1] = rrset("jellyfin", "CNAME", "server-64gb-storage.xberg.ber.ewwww.eu.", ttl=3600)

    result = diff_public_records(DERIVED, existing, ZONE, TTL)

    assert result["cname_upserts"] == [{"name": "jellyfin", "value": "server-64gb-storage.xberg.ber.ewwww.eu."}]


def test_cname_comparison_ignores_trailing_dot_and_case():
    existing = in_sync()
    existing[1] = rrset("jellyfin", "CNAME", "Server-64gb-Storage.xberg.ber.ewwww.eu")

    result = diff_public_records(DERIVED, existing, ZONE, TTL)

    assert result["cname_upserts"] == []


def test_legacy_a_record_at_a_cname_label_is_deleted_and_cname_published():
    existing = [
        rrset("server-64gb-storage.xberg.ber", "A", "100.80.1.116"),
        rrset("jellyfin", "A", "100.80.1.116"),
    ]

    result = diff_public_records(DERIVED, existing, ZONE, TTL)

    assert result["a_deletes"] == ["jellyfin"]
    assert result["cname_upserts"] == [{"name": "jellyfin", "value": "server-64gb-storage.xberg.ber.ewwww.eu."}]


def test_unrelated_records_are_left_alone():
    existing = in_sync() + [rrset("legacy", "A", "203.0.113.1"), rrset("www", "CNAME", "elsewhere.example.")]

    result = diff_public_records(DERIVED, existing, ZONE, TTL)

    assert result == {"a_upserts": [], "a_deletes": [], "cname_upserts": []}
