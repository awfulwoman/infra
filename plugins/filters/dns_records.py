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
                labels = entry.get("labels", compositions[composition_name])
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


class FilterModule(object):
    """Custom filters for deriving DNS records from inventory data"""

    def filters(self):
        return {
            "dns_records": self.dns_records,
        }

    def dns_records(self, hosts, compositions):
        from ansible.errors import AnsibleFilterError

        try:
            return derive_dns_records(hosts, compositions)
        except DuplicateLabelError as exc:
            raise AnsibleFilterError(str(exc))
