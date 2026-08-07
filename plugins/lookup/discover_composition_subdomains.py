#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Discover each composition-* role's declared DNS subdomains by reading its
own defaults/main.yaml directly — no Ansible variable rendering involved, so
a role's defaults can't collide with another's in a shared namespace, and a
stray Jinja expression (e.g. referencing ansible_facts) shows up as a broken
literal string rather than silently resolving against the wrong host.
"""

from pathlib import Path

import yaml


def discover_composition_subdomains(roles_dir):
    result = {}

    for defaults_path in sorted(Path(roles_dir).glob("composition-*/defaults/main.yaml")):
        composition_name = defaults_path.parent.parent.name.removeprefix("composition-")
        data = yaml.safe_load(defaults_path.read_text()) or {}

        if "composition_dns_subdomains" in data:
            result[composition_name] = data["composition_dns_subdomains"]

    return result
