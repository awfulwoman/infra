#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Derive the DNS record set (one A per host, one CNAME per service) from
inventory host data. The pure logic (derive_dns_records) has no dependency
on Ansible, so it can be unit tested directly; FilterModule is the thin
Ansible-facing adapter that translates a duplicate label into an
AnsibleFilterError.
"""


class DuplicateLabelError(ValueError):
    pass


def derive_dns_records(hosts, compositions):
    a_records = {}
    cnames = {}
    label_owners = {}

    for host_name, host in hosts.items():
        a_records[host_name] = {"name": host["fqdn"], "target": host["tailscale_ipv4"]}

        for entry in host["compositions"]:
            if isinstance(entry, dict):
                composition_name = entry["composition"]
                # Not entry.get("labels", compositions[composition_name]):
                # Python evaluates a .get() call's default argument eagerly
                # regardless of whether the key is present, so that would
                # raise KeyError for a role with no declared
                # composition_dns_subdomains even when labels is given and
                # the fallback is never actually used (composition-chives).
                labels = entry["labels"] if "labels" in entry else compositions[composition_name]
            else:
                composition_name = entry
                labels = compositions[composition_name]

            for label in labels:
                resolved_label = label.format(host=host_name)

                owner = label_owners.get(resolved_label)
                if owner is not None and owner != host_name:
                    raise DuplicateLabelError(
                        f"composition '{composition_name}' label '{resolved_label}' is claimed by both "
                        f"'{owner}' and '{host_name}'"
                    )
                label_owners[resolved_label] = host_name

                cnames[resolved_label] = host["fqdn"]

    return {"a_records": a_records, "cnames": cnames}


def _normalise(value):
    return value.rstrip(".").lower()


def diff_public_records(derived, existing, zone, ttl):
    """Compare the derived record set against the RRSets already in the public
    zone and return only what has to be written. Add-only, like the publish
    tasks it feeds: names outside the derived set are never touched."""
    current = {(r["name"], r["type"]): r for r in existing}

    def needs_write(name, type_, value):
        rrset = current.get((name, type_))
        if rrset is None or rrset.get("ttl") != ttl:
            return True
        return [_normalise(r["value"]) for r in rrset["records"]] != [_normalise(value)]

    a_upserts = [
        {"name": a["name"], "value": a["target"]}
        for a in derived["a_records"].values()
        if needs_write(a["name"], "A", a["target"])
    ]
    a_deletes = [label for label in derived["cnames"] if (label, "A") in current]
    cname_upserts = []
    for label, target in derived["cnames"].items():
        value = f"{target}.{zone}."
        if needs_write(label, "CNAME", value):
            cname_upserts.append({"name": label, "value": value})

    return {"a_upserts": a_upserts, "a_deletes": a_deletes, "cname_upserts": cname_upserts}


class FilterModule(object):
    """Custom filters for deriving DNS records from inventory data"""

    def filters(self):
        return {
            "dns_records": self.dns_records,
            "dns_public_changes": diff_public_records,
        }

    def dns_records(self, hosts, compositions):
        from ansible.errors import AnsibleFilterError

        try:
            return derive_dns_records(hosts, compositions)
        except DuplicateLabelError as exc:
            raise AnsibleFilterError(str(exc))
